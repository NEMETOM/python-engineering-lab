import os

from shared.config.settings import Settings


class TestSettingsDefaults:
    def test_kafka_broker_default(self):
        assert Settings.kafka_broker == os.getenv("KAFKA_BROKER", "localhost:9092")

    def test_db_url_default(self):
        assert Settings.db_url == os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/trades"
        )

    def test_log_level_default(self):
        assert Settings.log_level == os.getenv("LOG_LEVEL", "INFO")

    def test_kafka_broker_value_when_no_env(self):
        if "KAFKA_BROKER" not in os.environ:
            assert Settings.kafka_broker == "localhost:9092"

    def test_db_url_value_when_no_env(self):
        if "DATABASE_URL" not in os.environ:
            assert Settings.db_url == "postgresql://user:password@localhost:5432/trades"

    def test_log_level_value_when_no_env(self):
        if "LOG_LEVEL" not in os.environ:
            assert Settings.log_level == "INFO"


class TestSettingsInstance:
    def test_settings_instance_is_created(self):
        from shared.config.settings import settings

        assert isinstance(settings, Settings)

    def test_instance_has_kafka_broker(self):
        from shared.config.settings import settings

        assert hasattr(settings, "kafka_broker")

    def test_instance_has_db_url(self):
        from shared.config.settings import settings

        assert hasattr(settings, "db_url")

    def test_instance_has_log_level(self):
        from shared.config.settings import settings

        assert hasattr(settings, "log_level")
