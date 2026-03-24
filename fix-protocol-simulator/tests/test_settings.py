# fix-protocol-simulator/tests/test_settings.py

from fix_simulator.config.settings import Settings, settings


def test_default_host():
    assert settings.host == "127.0.0.1"


def test_default_port():
    assert settings.port == 9878


def test_default_sender_comp_id():
    assert settings.sender_comp_id == "EXCHANGE"


def test_default_target_comp_id():
    assert settings.target_comp_id == "CLIENT"


def test_custom_settings():
    s = Settings(host="0.0.0.0", port=5000)
    assert s.host == "0.0.0.0"
    assert s.port == 5000
