import importlib
import os


class TestDefaults:
    def test_kafka_broker_default(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {}, clear=True
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.KAFKA_BROKER == "localhost:9092"

    def test_notional_limit_default(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {}, clear=True
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.NOTIONAL_LIMIT == 1_000_000.0

    def test_fat_finger_pct_default(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {}, clear=True
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.FAT_FINGER_PCT == 10.0

    def test_gross_position_limit_default(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {}, clear=True
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.GROSS_POSITION_LIMIT == 10_000

    def test_net_position_limit_default(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {}, clear=True
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.NET_POSITION_LIMIT == 5_000

    def test_max_open_orders_default(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {}, clear=True
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.MAX_OPEN_ORDERS == 10


class TestTopicNames:
    def test_input_topic(self):
        import risk_service.config as cfg

        assert cfg.INPUT_TOPIC == "validated_orders"

    def test_approved_topic(self):
        import risk_service.config as cfg

        assert cfg.APPROVED_TOPIC == "risk_approved_orders"

    def test_rejected_topic(self):
        import risk_service.config as cfg

        assert cfg.REJECTED_TOPIC == "risk_rejected_orders"

    def test_trades_topic(self):
        import risk_service.config as cfg

        assert cfg.TRADES_TOPIC == "trades"

    def test_group_id(self):
        import risk_service.config as cfg

        assert cfg.GROUP_ID == "risk-service"


class TestEnvOverride:
    def test_kafka_broker_from_env(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {"KAFKA_BROKER": "broker:9093"}
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.KAFKA_BROKER == "broker:9093"

    def test_notional_limit_from_env(self):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {"RISK_NOTIONAL_LIMIT": "500000"}
        ):
            import risk_service.config as cfg

            importlib.reload(cfg)
            assert cfg.NOTIONAL_LIMIT == 500_000.0
