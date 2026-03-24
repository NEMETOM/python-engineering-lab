#fix-protocol-simulator/tests/test_logger.py

import logging

from fix_simulator.utils.logger import setup_logger


def test_setup_logger_level(monkeypatch):
    called = {}

    def fake_basicConfig(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basicConfig)
    setup_logger()

    assert called["level"] == logging.INFO


def test_setup_logger_format(monkeypatch):
    called = {}

    def fake_basicConfig(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basicConfig)
    setup_logger()

    assert "%(levelname)s" in called["format"]
    assert "%(module)s" in called["format"]
    assert "%(message)s" in called["format"]


def test_setup_logger_datefmt(monkeypatch):
    called = {}

    def fake_basicConfig(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basicConfig)
    setup_logger()

    assert called["datefmt"] == "%Y-%m-%d %H:%M:%S"
