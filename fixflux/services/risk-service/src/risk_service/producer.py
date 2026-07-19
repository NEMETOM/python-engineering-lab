from opentelemetry import trace

from risk_service import config
from shared.infrastructure.kafka_client import create_exec_report_producer, create_producer
from shared.observability.metrics import exec_reports_emitted
from shared.observability.tracing import inject_ctx
from shared.schemas.execution_report_event import ExecutionReportEvent

_tracer = trace.get_tracer("risk-service")


class RiskProducer:
    def __init__(self):
        self._producer = create_producer()
        self._exec_producer = create_exec_report_producer()

    def approve(self, order_dict: dict) -> None:
        data = {**order_dict}
        inject_ctx(data)
        self._producer.send(config.APPROVED_TOPIC, data)

    def reject(self, rejection_dict: dict) -> None:
        data = {**rejection_dict}
        inject_ctx(data)
        self._producer.send(config.REJECTED_TOPIC, data)

    def send_exec_report(self, report: ExecutionReportEvent) -> None:
        with _tracer.start_as_current_span("risk-service.send_exec_report") as span:
            span.set_attribute("exec_type", report.exec_type)
            span.set_attribute("order.id", report.order_id)
            span.set_attribute("client.id", report.client_id)
            data = report.model_dump(mode="json")
            inject_ctx(data)
            self._exec_producer.send(config.EXEC_REPORTS_TOPIC, data)
            exec_reports_emitted.labels(
                exec_type=report.exec_type, service="risk-service"
            ).inc()
