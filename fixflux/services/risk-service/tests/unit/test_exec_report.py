from datetime import datetime, timezone
from unittest.mock import MagicMock

from risk_service.checker import RiskChecker
from risk_service.consumer import handle_order
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
        client_id="CLIENT-A",
    )
    defaults.update(overrides)
    return defaults


class TestApprovedOrderExecReport:
    def setup_method(self):
        self.store = PositionStore()
        self.last_prices = {}
        self.producer = MagicMock()

    def test_send_exec_report_called_on_approve(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        self.producer.send_exec_report.assert_called_once()

    def test_exec_report_exec_type_new(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.exec_type == "0"

    def test_exec_report_ord_status_new(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.ord_status == "0"

    def test_exec_report_order_id(self):
        handle_order(
            _order_dict(order_id="O-APPROVED"),
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.order_id == "O-APPROVED"

    def test_exec_report_client_id(self):
        handle_order(
            _order_dict(client_id="FIRM-X"),
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.client_id == "FIRM-X"

    def test_exec_report_symbol(self):
        handle_order(
            _order_dict(symbol="MSFT"),
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.symbol == "MSFT"

    def test_exec_report_side(self):
        handle_order(
            _order_dict(side="SELL"),
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.side == "SELL"

    def test_exec_report_leaves_qty_equals_order_qty(self):
        handle_order(
            _order_dict(quantity=15),
            _checker(),
            self.store,
            self.last_prices,
            self.producer,
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.leaves_qty == 15
        assert report.order_qty == 15

    def test_exec_report_cum_qty_zero_on_new(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.cum_qty == 0

    def test_exec_report_reason_none_on_approve(self):
        handle_order(
            _order_dict(), _checker(), self.store, self.last_prices, self.producer
        )
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.reason is None


class TestRejectedOrderExecReport:
    def setup_method(self):
        self.store = PositionStore()
        self.last_prices = {}
        self.producer = MagicMock()

    def _reject_order(self, **overrides):
        handle_order(
            _order_dict(price=9_999_999.0, quantity=9_999_999, **overrides),
            _checker(notional_limit=1.0),
            self.store,
            self.last_prices,
            self.producer,
        )

    def test_send_exec_report_called_on_reject(self):
        self._reject_order()
        self.producer.send_exec_report.assert_called_once()

    def test_exec_report_exec_type_rejected(self):
        self._reject_order()
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.exec_type == "8"

    def test_exec_report_ord_status_rejected(self):
        self._reject_order()
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.ord_status == "8"

    def test_exec_report_leaves_qty_zero_on_reject(self):
        self._reject_order()
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.leaves_qty == 0

    def test_exec_report_cum_qty_zero_on_reject(self):
        self._reject_order()
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.cum_qty == 0

    def test_exec_report_reason_populated_on_reject(self):
        self._reject_order()
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.reason is not None
        assert len(report.reason) > 0

    def test_exec_report_order_id_on_reject(self):
        self._reject_order(order_id="O-REJECTED")
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.order_id == "O-REJECTED"

    def test_exec_report_client_id_on_reject(self):
        self._reject_order(client_id="FIRM-RJCT")
        report = self.producer.send_exec_report.call_args[0][0]
        assert report.client_id == "FIRM-RJCT"


class TestExecReportBestEffort:
    def setup_method(self):
        self.store = PositionStore()
        self.last_prices = {}

    def test_exec_report_failure_does_not_block_approve(self):
        producer = MagicMock()
        producer.send_exec_report.side_effect = RuntimeError("Kafka down")
        handle_order(_order_dict(), _checker(), self.store, self.last_prices, producer)
        producer.approve.assert_called_once()

    def test_exec_report_failure_does_not_block_reject(self):
        producer = MagicMock()
        producer.send_exec_report.side_effect = RuntimeError("Kafka down")
        handle_order(
            _order_dict(price=9_999_999.0, quantity=9_999_999),
            _checker(notional_limit=1.0),
            self.store,
            self.last_prices,
            producer,
        )
        producer.reject.assert_called_once()

    def test_exec_report_failure_does_not_raise(self):
        producer = MagicMock()
        producer.send_exec_report.side_effect = RuntimeError("Kafka down")
        handle_order(_order_dict(), _checker(), self.store, self.last_prices, producer)


class TestMutualExclusion:
    def setup_method(self):
        self.store = PositionStore()
        self.last_prices = {}

    def test_approved_order_does_not_call_reject(self):
        producer = MagicMock()
        handle_order(_order_dict(), _checker(), self.store, self.last_prices, producer)
        producer.reject.assert_not_called()

    def test_rejected_order_does_not_call_approve(self):
        producer = MagicMock()
        handle_order(
            _order_dict(price=9_999_999.0, quantity=9_999_999),
            _checker(notional_limit=1.0),
            self.store,
            self.last_prices,
            producer,
        )
        producer.approve.assert_not_called()

    def test_malformed_order_does_not_emit_exec_report(self):
        producer = MagicMock()
        handle_order(
            {"bad": "data"}, _checker(), self.store, self.last_prices, producer
        )
        producer.send_exec_report.assert_not_called()
