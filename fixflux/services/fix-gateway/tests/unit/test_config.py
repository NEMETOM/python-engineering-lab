# fixflux/services/fix-gateway/tests/unit/test_config.py

from fix_gateway.config import Settings, settings


def test_default_settings():

    s = Settings()

    assert s.host == "0.0.0.0"
    assert s.port == 9878
    assert s.buffer_size == 4096
    assert s.fix_delimiter == "|"


def test_custom_settings():

    s = Settings(host="127.0.0.1", port=5000, buffer_size=1024)

    assert s.host == "127.0.0.1"
    assert s.port == 5000
    assert s.buffer_size == 1024


def test_settings_singleton_has_defaults():

    assert settings.host == "0.0.0.0"
    assert settings.port == 9878
