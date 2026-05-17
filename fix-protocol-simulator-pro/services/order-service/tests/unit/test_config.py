import importlib
import os
from unittest.mock import patch


class TestSettings:
    def test_default_kafka_broker(self):
        with patch.dict(os.environ, {}, clear=True):
            import order_service.config as config_module

            importlib.reload(config_module)
            assert config_module.settings.kafka_broker == "kafka:9092"

    def test_kafka_broker_from_env(self):
        with patch.dict(os.environ, {"KAFKA_BROKER": "localhost:9093"}):
            import order_service.config as config_module

            importlib.reload(config_module)
            assert config_module.settings.kafka_broker == "localhost:9093"
