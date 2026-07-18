from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from risk_service.checker import RiskChecker
from risk_service.consumer import _build_checker, handle_order, handle_trade, run
from risk_service.position_store import PositionStore


def _checker(**overrides):
    defaults = dict(
        notional_limit=1_000_000.0,
        fat_finger_pct=10.0,
        gross_position_limit=10_000,
        net_position_limit=5_000,
        max_open_orders=10,
    )
    defaults.update(overrides)
    return RiskChecker(**defaults)


def _order_dict(**overrides):
    defaults = dict(
        order_id="O1",
        symbol="AAPL",
        side="BUY",
        price=100.0,
        quantity=10,
        timestamp=datetime.now(timezone.utc).isoformat(),
        client_id="C1",
    )
    defaults.update(overrides)
    return defaults


def _trade_dict(**overrides):
    defaults = dict(
        trade_id="T1",
        symbol="AAPL",
        buy_order_id="O-BUY",
        sell_order_id="O-SELL",
        price=100.0,
        quantity=50,
    )
    defaults.update(overrides)
    return defaults


class TestHandleOrder:
    def setup_method(self):
        self.store = PositionStore()
        self.last_prices = {}
        self.producer = MagicMock()

    def test_passing_order_calls_approve(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        self.producer.approve.assert_called_once()

    def test_passing_order_does_not_call_reject(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        self.producer.reject.assert_not_called()

    def test_passing_order_forwards_original_dict(self):
        value = _order_dict()
        handle_order(value, _checker(), self.store, self.last_prices, self.producer)
        self.producer.approve.assert_called_once_with(value)

    def test_rejected_order_calls_reject(self):
        handle_order(
            _order_dict(price=9_999_999.0, quantity=9_999_999),
            _checker(notional_limit=1.0),
            self.store,
            self.last_prices,
            self.producer,
        )
        self.producer.reject.assert_called_once()

    def test_rejected_order_does_not_call_approve(self):
        handle_order(
            _order_dict(price=9_999_999.0, quantity=9_999_999),
            _checker(notional_limit=1.0),
            self.store,
            self.last_prices,
            self.producer,
        )
        self.producer.approve.assert_not_called()

    def test_approved_order_is_recorded_in_store(self):
        handle_order(
            _order_dict(order_id="O1"),
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )
        assert self.store.get_open_order_count("C1") == 1

    def test_rejected_order_is_not_recorded_in_store(self):
        handle_order(
            _order_dict(price=9_999.0, quantity=9_999),
            _checker(notional_limit=1.0),
            self.store,
            self.last_prices,
            self.producer,
        )
        assert self.store.get_open_order_count("C1") == 0

    def test_malformed_dict_does_not_raise(self):
        handle_order(
            {"not": "a valid order"},
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )

    def test_malformed_dict_does_not_produce(self):
        handle_order(
            {"bad": "data"}, _checker(), self.store, self.last_prices, self.producer
        )
        self.producer.approve.assert_not_called()
        self.producer.reject.assert_not_called()


class TestHandleTrade:
    def setup_method(self):
        self.store = PositionStore()
        self.last_prices = {}

    def test_trade_updates_last_price(self):
        handle_trade(
            _trade_dict(symbol="AAPL", price=175.5), self.store, self.last_prices
        )
        assert self.last_prices["AAPL"] == 175.5

    def test_trade_overwrites_stale_last_price(self):
        self.last_prices["AAPL"] = 100.0
        handle_trade(
            _trade_dict(symbol="AAPL", price=200.0), self.store, self.last_prices
        )
        assert self.last_prices["AAPL"] == 200.0

    def test_trade_fills_buy_order(self):
        self.store.record_open_order("O-BUY", "C1", "AAPL", "BUY", 50)
        handle_trade(
            _trade_dict(buy_order_id="O-BUY", sell_order_id="O-SELL"),
            self.store,
            self.last_prices,
        )
        assert self.store.get_open_order_count("C1") == 0

    def test_trade_fills_sell_order(self):
        self.store.record_open_order("O-SELL", "C2", "AAPL", "SELL", 50)
        handle_trade(
            _trade_dict(buy_order_id="O-BUY", sell_order_id="O-SELL"),
            self.store,
            self.last_prices,
        )
        assert self.store.get_open_order_count("C2") == 0

    def test_trade_updates_net_position(self):
        self.store.record_open_order("O-BUY", "C1", "AAPL", "BUY", 50)
        handle_trade(_trade_dict(buy_order_id="O-BUY"), self.store, self.last_prices)
        assert self.store.get_net_position("C1", "AAPL") == 50

    def test_malformed_trade_does_not_raise(self):
        handle_trade({"not": "a valid trade"}, self.store, self.last_prices)

    def test_malformed_trade_does_not_corrupt_last_prices(self):
        self.last_prices["AAPL"] = 100.0
        handle_trade({"garbage": True}, self.store, self.last_prices)
        assert self.last_prices["AAPL"] == 100.0


class TestBuildChecker:
    def test_returns_risk_checker_instance(self):
        checker = _build_checker()
        assert isinstance(checker, RiskChecker)

    def test_uses_config_defaults(self):
        from risk_service import config

        checker = _build_checker()
        assert checker.notional_limit == config.NOTIONAL_LIMIT
        assert checker.fat_finger_pct == config.FAT_FINGER_PCT
        assert checker.max_open_orders == config.MAX_OPEN_ORDERS


def _make_order_msg():
    msg = MagicMock()
    msg.topic = "validated_orders"
    msg.value = {
        "order_id": "O1",
        "symbol": "AAPL",
        "side": "BUY",
        "price": 100.0,
        "quantity": 10,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": "CLIENT-A",
    }
    return msg


def _make_trade_msg():
    msg = MagicMock()
    msg.topic = "trades"
    msg.value = {
        "trade_id": "T1",
        "symbol": "AAPL",
        "buy_order_id": "O-BUY",
        "sell_order_id": "O-SELL",
        "price": 100.0,
        "quantity": 10,
    }
    return msg


class TestRun:
    def test_run_processes_order_message(self):
        with patch(
            "risk_service.consumer.KafkaConsumer", return_value=[_make_order_msg()]
        ):
            with patch("risk_service.consumer.RiskProducer") as mock_producer_cls:
                mock_producer_cls.return_value = MagicMock()
                run()

    def test_run_processes_trade_message(self):
        with patch(
            "risk_service.consumer.KafkaConsumer", return_value=[_make_trade_msg()]
        ):
            with patch("risk_service.consumer.RiskProducer") as mock_producer_cls:
                mock_producer_cls.return_value = MagicMock()
                run()

    def test_run_calls_handle_order_for_order_topic(self):
        with patch(
            "risk_service.consumer.KafkaConsumer", return_value=[_make_order_msg()]
        ):
            with patch("risk_service.consumer.RiskProducer") as mock_producer_cls:
                mock_producer = MagicMock()
                mock_producer_cls.return_value = mock_producer
                run()
                mock_producer.approve.assert_called_once()

    def test_run_calls_handle_trade_for_trades_topic(self):
        with patch(
            "risk_service.consumer.KafkaConsumer", return_value=[_make_trade_msg()]
        ):
            with patch("risk_service.consumer.RiskProducer") as mock_producer_cls:
                mock_producer_cls.return_value = MagicMock()
                with patch("risk_service.consumer.handle_trade") as mock_handle_trade:
                    run()
                    mock_handle_trade.assert_called_once()
