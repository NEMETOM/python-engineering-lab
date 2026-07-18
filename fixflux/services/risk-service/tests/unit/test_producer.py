from unittest.mock import MagicMock, patch

import pytest

from risk_service.producer import RiskProducer
from shared.schemas.execution_report_event import ExecutionReportEvent


def _make_report(**overrides):
    defaults = dict(
        order_id="O1",
        cl_ord_id="O1",
        client_id="CLIENT-A",
        exec_type="0",
        ord_status="0",
        symbol="AAPL",
        side="BUY",
        price=100.0,
        order_qty=10,
        leaves_qty=10,
        cum_qty=0,
    )
    return ExecutionReportEvent(**{**defaults, **overrides})


@pytest.fixture
def mock_kafka_producer():
    with patch("risk_service.producer.create_producer") as mock_create:
        mock_kafka = MagicMock()
        mock_create.return_value = mock_kafka
        yield mock_kafka


@pytest.fixture
def producer(mock_kafka_producer):
    return RiskProducer()


class TestApprove:
    def test_sends_to_approved_topic(self, producer, mock_kafka_producer):
        producer.approve({"order_id": "O1"})
        topic = mock_kafka_producer.send.call_args[0][0]
        assert topic == "risk_approved_orders"

    def test_payload_contains_original_fields(self, producer, mock_kafka_producer):
        producer.approve({"order_id": "O1", "symbol": "AAPL"})
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["order_id"] == "O1"
        assert payload["symbol"] == "AAPL"

    def test_called_once(self, producer, mock_kafka_producer):
        producer.approve({"order_id": "O1"})
        mock_kafka_producer.send.assert_called_once()


class TestReject:
    def test_sends_to_rejected_topic(self, producer, mock_kafka_producer):
        producer.reject({"order_id": "O1", "reason": "Limit exceeded"})
        topic = mock_kafka_producer.send.call_args[0][0]
        assert topic == "risk_rejected_orders"

    def test_payload_contains_reason(self, producer, mock_kafka_producer):
        producer.reject({"order_id": "O1", "reason": "Fat finger"})
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["reason"] == "Fat finger"

    def test_called_once(self, producer, mock_kafka_producer):
        producer.reject({"order_id": "O1"})
        mock_kafka_producer.send.assert_called_once()


class TestSendExecReport:
    def test_sends_to_exec_reports_topic(self, producer, mock_kafka_producer):
        producer.send_exec_report(_make_report())
        topic = mock_kafka_producer.send.call_args[0][0]
        assert topic == "execution_reports"

    def test_payload_contains_exec_type(self, producer, mock_kafka_producer):
        producer.send_exec_report(_make_report(exec_type="0"))
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["exec_type"] == "0"

    def test_payload_contains_order_id(self, producer, mock_kafka_producer):
        producer.send_exec_report(_make_report(order_id="O-SENT"))
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["order_id"] == "O-SENT"

    def test_payload_contains_client_id(self, producer, mock_kafka_producer):
        producer.send_exec_report(_make_report(client_id="FIRM-X"))
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["client_id"] == "FIRM-X"

    def test_called_once(self, producer, mock_kafka_producer):
        producer.send_exec_report(_make_report())
        mock_kafka_producer.send.assert_called_once()

    def test_rejected_report_sends_exec_type_8(self, producer, mock_kafka_producer):
        producer.send_exec_report(_make_report(exec_type="8", ord_status="8"))
        payload = mock_kafka_producer.send.call_args[0][1]
        assert payload["exec_type"] == "8"

    def test_metric_incremented_with_correct_labels(
        self, producer, mock_kafka_producer
    ):
        with patch("risk_service.producer.exec_reports_emitted") as mock_metric:
            producer.send_exec_report(_make_report(exec_type="0"))
            mock_metric.labels.assert_called_once_with(
                exec_type="0", service="risk-service"
            )
            mock_metric.labels.return_value.inc.assert_called_once()

    def test_metric_label_exec_type_8(self, producer, mock_kafka_producer):
        with patch("risk_service.producer.exec_reports_emitted") as mock_metric:
            producer.send_exec_report(_make_report(exec_type="8", ord_status="8"))
            mock_metric.labels.assert_called_once_with(
                exec_type="8", service="risk-service"
            )
