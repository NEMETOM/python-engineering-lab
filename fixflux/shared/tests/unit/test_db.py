import importlib

import pytest
import yaml

from shared.config import _loader


@pytest.fixture
def db_module(monkeypatch):
    """Import shared.infrastructure.db against an in-memory SQLite URL.

    The module builds its engine at import time from build_db_url(), so it is
    (re)loaded under a controlled DATABASE_URL instead of whatever the machine
    running the tests happens to have configured.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    from shared.infrastructure import db

    return importlib.reload(db)


class TestDbModule:
    def test_engine_uses_the_configured_url(self, db_module):
        assert str(db_module.engine.url) == "sqlite://"

    def test_sessions_are_bound_to_the_engine_without_autoflush(self, db_module):
        session = db_module.SessionLocal()
        try:
            assert session.get_bind() is db_module.engine
            assert session.autoflush is False
        finally:
            session.close()

    def test_models_declared_on_base_register_their_tables(self, db_module):
        from sqlalchemy import Column, Integer

        class _Probe(db_module.Base):
            __tablename__ = "probe"
            id = Column(Integer, primary_key=True)

        assert "probe" in db_module.Base.metadata.tables


def _make_db_config(**overrides):
    defaults = {
        "user": "fixuser",
        "password": "fixpass",
        "host": "postgres",
        "port": 5432,
        "name": "fixdb",
    }
    return {"database": {**defaults, **overrides}}


class TestBuildDbUrl:
    def test_database_url_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@h:1/d")
        assert _loader.build_db_url() == "postgresql+psycopg2://u:p@h:1/d"

    def test_falls_back_to_config_yaml(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(_make_db_config()))
        monkeypatch.setattr(_loader, "_CONFIG_PATH", path)
        assert (
            _loader.build_db_url()
            == "postgresql+psycopg2://fixuser:fixpass@postgres:5432/fixdb"
        )

    def test_password_special_characters_are_url_escaped(self, monkeypatch, tmp_path):
        # An unescaped "@" or ":" in the password would be parsed as the host
        # separator and produce a connection URL to the wrong host.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(_make_db_config(password="p@ss:w/rd")))
        monkeypatch.setattr(_loader, "_CONFIG_PATH", path)
        assert "fixuser:p%40ss%3Aw%2Frd@postgres" in _loader.build_db_url()
