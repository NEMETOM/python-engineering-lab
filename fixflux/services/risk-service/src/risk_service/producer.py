from risk_service import config
from shared.infrastructure.kafka_client import create_producer
from shared.observability.metrics import exec_reports_emitted
from shared.observability.tracing import inject_ctx
from shared.schemas.execution_report_event import ExecutionReportEvent


class RiskProducer:
    def __init__(self):
        self._producer = create_producer()

    def approve(self, order_dict: dict) -> None:
        data = {**order_dict}
        inject_ctx(data)
        self._producer.send(config.APPROVED_TOPIC, data)

    def reject(self, rejection_dict: dict) -> None:
        data = {**rejection_dict}
        inject_ctx(data)
        self._producer.send(config.REJECTED_TOPIC, data)

    def send_exec_report(self, report: ExecutionReportEvent) -> None:
        data = report.model_dump(mode="json")
        inject_ctx(data)
        self._producer.send(config.EXEC_REPORTS_TOPIC, data)
        exec_reports_emitted.labels(
            exec_type=report.exec_type, service="risk-service"
        ).inc()
