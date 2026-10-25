import time
from collections.abc import Callable

from prometheus_client import start_http_server
from sqlalchemy.exc import OperationalError

from reporting_service import config
from reporting_service.enricher import ReportEnricher
from reporting_service.infrastructure.kafka_client import create_consumer
from reporting_service.repository import ReportRepository
from reporting_service.schemas import RegulatoryTradeReport, TradeEvent
from reporting_service.utils.logger import configure_logging, get_logger
from shared.infrastructure.db import Base, engine
from shared.observability.metrics import (
    regulatory_report_latency_seconds,
    regulatory_reports,
)
from shared.observability.tracing import extract_ctx, init_tracer

configure_logging()
logger = get_logger(__name__)

_tracer = init_tracer("reporting-service")


def save_with_retry(
    repo: ReportRepository,
    report: RegulatoryTradeReport,
    sleep: Callable[[float], None] = time.sleep,
    max_backoff: float = config.DB_RETRY_MAX_BACKOFF_SECONDS,
) -> bool:
    """Retry connection-level DB failures until the report is stored. Only
    OperationalError is retried; anything else is a data problem that retrying
    can't fix and is left to the caller."""
    backoff = 1.0
    while True:
        try:
            return repo.save(report)
        except OperationalError as exc:
            logger.warning(
                f"database unavailable, retrying trade {report.trade_id} "
                f"in {backoff:.0f}s: {exc}"
            )
            sleep(backoff)
            backoff = min(backoff * 2, max_backoff)


def handle(
    value: dict,
    enricher: ReportEnricher,
    repo: ReportRepository,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    ctx = extract_ctx(value)
    with _tracer.start_as_current_span(
        "reporting-service.process", context=ctx
    ) as span:
        try:
            trade = TradeEvent(**value)
            span.set_attribute("trade.id", trade.trade_id)
            report = enricher.enrich(trade)
            inserted = save_with_retry(repo, report, sleep=sleep)
        except Exception as e:  # noqa: BLE001
            span.record_exception(e)
            logger.error(f"failed to report trade {value} reason={e}")
            return

        outcome = report.status if inserted else "DUPLICATE"
        span.set_attribute("regulatory.status", outcome)
        regulatory_reports.labels(status=outcome).inc()
        if inserted and report.publication_latency_ms is not None:
            regulatory_report_latency_seconds.observe(
                report.publication_latency_ms / 1000
            )
        logger.info(
            f"regulatory_report | trade={report.trade_id} symbol={report.symbol} "
            f"status={outcome} latency_ms={report.publication_latency_ms} "
            f"deadline_breached={report.deadline_breached} "
            f"reason={report.status_reason!r}"
        )


def run() -> None:
    start_http_server(config.METRICS_PORT)
    logger.info(f"metrics server started on :{config.METRICS_PORT}")
    Base.metadata.create_all(bind=engine)
    enricher = ReportEnricher(config.load_reference_data())
    repo = ReportRepository()
    consumer = create_consumer(config.INPUT_TOPIC, config.GROUP_ID)
    logger.info("reporting-service started")
    for msg in consumer:
        handle(msg.value, enricher, repo)


if __name__ == "__main__":  # pragma: no cover
    run()
