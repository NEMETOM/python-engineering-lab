from unittest.mock import MagicMock, patch

import pytest

from matching_engine.models import Trade
from matching_engine.producer import Producer


def _make_trade(**overrides):
    defaults = dict(
        trade_id="T1",
        symbol="AAPL",
        buy_order_id="B1",
        sell_order_id="S1",
        price=150.0,
        quantity=20,
        buy_client_id="CLIENT-BUY",
        sell_client_id="CLIENT-SELL",
        buy_order_qty=20,
        sell_order_qty=20,
    )
    return Trade(**{**defaults, **overrides})


@pytest.fixture
def mock_kafka_producer():
    with patch("matching_engine.producer.create_producer") as mock_create:
        mock_producer = MagicMock()
        mock_create.return_value = mock_producer
        yield mock_producer


@pytest.fixture
def producer(mock_kafka_producer):
    return Producer()


class TestSendExecReports:
    def test_emits_two_kafka_messages_per_trade(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade())
        assert mock_kafka_producer.send.call_count == 2

    def test_both_messages_go_to_execution_reports_topic(
        self, producer, mock_kafka_producer
    ):
        producer.send_exec_reports(_make_trade())
        for c in mock_kafka_producer.send.call_args_list:
            assert c[0][0] == "execution_reports"

    def test_buyer_report_has_buy_side(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade())
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        buy_reports = [p for p in payloads if p["side"] == "BUY"]
        assert len(buy_reports) == 1

    def test_seller_report_has_sell_side(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade())
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        sell_reports = [p for p in payloads if p["side"] == "SELL"]
        assert len(sell_reports) == 1

    def test_buyer_report_has_correct_order_id(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(buy_order_id="BUY-ORD-99"))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        buy_report = next(p for p in payloads if p["side"] == "BUY")
        assert buy_report["order_id"] == "BUY-ORD-99"

    def test_seller_report_has_correct_order_id(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(sell_order_id="SELL-ORD-77"))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        sell_report = next(p for p in payloads if p["side"] == "SELL")
        assert sell_report["order_id"] == "SELL-ORD-77"

    def test_buyer_report_has_correct_client_id(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(buy_client_id="FIRM-B"))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        buy_report = next(p for p in payloads if p["side"] == "BUY")
        assert buy_report["client_id"] == "FIRM-B"

    def test_seller_report_has_correct_client_id(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(sell_client_id="FIRM-S"))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        sell_report = next(p for p in payloads if p["side"] == "SELL")
        assert sell_report["client_id"] == "FIRM-S"

    def test_exec_type_is_fill(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade())
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        for p in payloads:
            assert p["exec_type"] == "F"

    def test_ord_status_is_filled(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade())
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        for p in payloads:
            assert p["ord_status"] == "2"

    def test_last_px_equals_trade_price(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(price=123.45))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        for p in payloads:
            assert p["last_px"] == 123.45

    def test_last_qty_equals_trade_quantity(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(quantity=7))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        for p in payloads:
            assert p["last_qty"] == 7

    def test_leaves_qty_is_zero(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade())
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        for p in payloads:
            assert p["leaves_qty"] == 0

    def test_symbol_propagated(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(symbol="TSLA"))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        for p in payloads:
            assert p["symbol"] == "TSLA"

    def test_buy_order_qty_propagated(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(buy_order_qty=50))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        buy_report = next(p for p in payloads if p["side"] == "BUY")
        assert buy_report["order_qty"] == 50

    def test_sell_order_qty_propagated(self, producer, mock_kafka_producer):
        producer.send_exec_reports(_make_trade(sell_order_qty=30))
        payloads = [c[0][1] for c in mock_kafka_producer.send.call_args_list]
        sell_report = next(p for p in payloads if p["side"] == "SELL")
        assert sell_report["order_qty"] == 30


class TestExecReportsMetric:
    def test_metric_incremented_twice_per_trade(self, producer, mock_kafka_producer):
        with patch("matching_engine.producer.exec_reports_emitted") as mock_metric:
            producer.send_exec_reports(_make_trade())
            assert mock_metric.labels.call_count == 2

    def test_metric_label_exec_type_is_fill(self, producer, mock_kafka_producer):
        with patch("matching_engine.producer.exec_reports_emitted") as mock_metric:
            producer.send_exec_reports(_make_trade())
            for c in mock_metric.labels.call_args_list:
                assert c.kwargs["exec_type"] == "F"

    def test_metric_label_service_is_matching_engine(
        self, producer, mock_kafka_producer
    ):
        with patch("matching_engine.producer.exec_reports_emitted") as mock_metric:
            producer.send_exec_reports(_make_trade())
            for c in mock_metric.labels.call_args_list:
                assert c.kwargs["service"] == "matching-engine"


class TestExecReportsBestEffort:
    def test_kafka_error_does_not_raise(self, producer, mock_kafka_producer):
        mock_kafka_producer.send.side_effect = RuntimeError("broker down")
        producer.send_exec_reports(_make_trade())  # must not raise

    def test_kafka_error_on_first_does_not_prevent_second(
        self, producer, mock_kafka_producer
    ):
        call_count = 0

        def flaky_send(topic, data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("first call fails")

        mock_kafka_producer.send.side_effect = flaky_send
        producer.send_exec_reports(_make_trade())
        assert call_count == 2
