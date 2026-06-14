from market_data_service.config import Settings, settings


def test_settings_is_instance_of_settings():

    assert isinstance(settings, Settings)


def test_settings_publish_interval_default():

    assert settings.publish_interval == 10
