from unittest.mock import MagicMock, patch


class TestCreateConsumer:
    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_creates_kafka_consumer(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_consumer

        create_consumer("trades", "trade-store")
        mock_cls.assert_called_once()

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_subscribes_to_correct_topic(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_consumer

        create_consumer("trades", "trade-store")
        args, _ = mock_cls.call_args
        assert args[0] == "trades"

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_sets_group_id(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_consumer

        create_consumer("trades", "trade-store")
        _, kwargs = mock_cls.call_args
        assert kwargs["group_id"] == "trade-store"

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_uses_configured_broker(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_consumer

        create_consumer("trades", "trade-store")
        _, kwargs = mock_cls.call_args
        assert kwargs["bootstrap_servers"] == "localhost:9092"

    @patch("shared.infrastructure.kafka_client.KafkaConsumer")
    def test_sets_earliest_offset_reset(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_consumer

        create_consumer("trades", "trade-store")
        _, kwargs = mock_cls.call_args
        assert kwargs["auto_offset_reset"] == "earliest"


class TestCreateProducer:
    @patch("shared.infrastructure.kafka_client.KafkaProducer")
    def test_creates_kafka_producer(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_producer

        create_producer()
        mock_cls.assert_called_once()

    @patch("shared.infrastructure.kafka_client.KafkaProducer")
    def test_uses_configured_broker(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from trade_store.infrastructure.kafka_client import create_producer

        create_producer()
        _, kwargs = mock_cls.call_args
        assert kwargs["bootstrap_servers"] == "localhost:9092"
