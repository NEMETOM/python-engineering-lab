import importlib
import os
from unittest.mock import patch


class TestDefaultSettings:
    def test_default_kafka_broker(self):
        with patch.dict(os.environ, {}, clear=False):
            import trade_store.config as cfg

            importlib.reload(cfg)
            assert cfg.Settings().kafka_broker == "kafka:9092"

    def test_default_database_url(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DATABASE_URL", None)
            import trade_store.config as cfg

            importlib.reload(cfg)
            assert (
                cfg.Settings().db_url
                == "postgresql://user:password@postgres:5432/trades"
            )


class TestEnvOverrides:
    def test_kafka_broker_env_override(self):
        with patch.dict(os.environ, {"KAFKA_BROKER": "localhost:9093"}):
            import trade_store.config as cfg

            importlib.reload(cfg)
            assert cfg.Settings().kafka_broker == "localhost:9093"

    def test_database_url_env_override(self):
        custom_url = "postgresql://admin:secret@myhost:5432/mydb"
        with patch.dict(os.environ, {"DATABASE_URL": custom_url}):
            import trade_store.config as cfg

            importlib.reload(cfg)
            assert cfg.Settings().db_url == custom_url
