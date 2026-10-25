import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://localhost/fixdb")

from behave import given, then, when

from reporting_service import consumer
from reporting_service.config import load_reference_data
from reporting_service.enricher import ReportEnricher
from reporting_service.lei import is_valid_lei
from reporting_service.schemas import TradeEvent

NOW = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)


def _make_enricher():
    return ReportEnricher(load_reference_data(), clock=lambda: NOW)


class _InMemoryRepository:
    """Mimics the trade_id unique constraint + ON CONFLICT DO NOTHING."""

    def __init__(self):
        self.rows = {}

    def save(self, report):
        if report.trade_id in self.rows:
            return False
        self.rows[report.trade_id] = report
        return True


@given(
    'a trade in "{symbol}" between "{buyer}" and "{seller}" executed {seconds:d} '
    "seconds ago"
)
def step_given_trade(context, symbol, buyer, seller, seconds):
    context.payload = {
        "trade_id": f"T-{symbol}-{buyer}-{seconds}",
        "symbol": symbol,
        "buy_order_id": "B1",
        "sell_order_id": "S1",
        "price": 100.0,
        "quantity": 10,
        "buy_client_id": buyer,
        "sell_client_id": seller,
        "timestamp": (NOW - timedelta(seconds=seconds)).isoformat(),
    }


@when("the trade is reported")
def step_when_reported(context):
    context.report = _make_enricher().enrich(TradeEvent(**context.payload))


@when("the same trade message is consumed {times:d} times")
def step_when_consumed_repeatedly(context, times):
    context.repo = _InMemoryRepository()
    with patch.object(consumer, "regulatory_reports") as counter:
        for _ in range(times):
            consumer.handle(context.payload, _make_enricher(), context.repo)
    context.outcomes = [c.kwargs["status"] for c in counter.labels.call_args_list]


@then('the report status is "{status}"')
def step_then_status(context, status):
    assert context.report.status == status, (
        context.report.status,
        context.report.status_reason,
    )


@then("the report carries valid LEIs for both parties")
def step_then_valid_leis(context):
    assert is_valid_lei(context.report.buyer_lei)
    assert is_valid_lei(context.report.seller_lei)


@then(
    'the report has CFI code "{cfi}" and trading capacity "{capacity}" for both sides'
)
def step_then_cfi_and_capacity(context, cfi, capacity):
    assert context.report.cfi_code == cfi
    assert context.report.buyer_trading_capacity == capacity
    assert context.report.seller_trading_capacity == capacity


@then('the status reason mentions "{text}"')
def step_then_reason(context, text):
    assert text in (context.report.status_reason or ""), context.report.status_reason


@then('the publication deadline breached flag is "{breached}"')
def step_then_breached(context, breached):
    assert context.report.deadline_breached is (breached == "true")


@then('the report keeps buyer client ID "{buyer}"')
def step_then_keeps_client_id(context, buyer):
    assert context.report.buyer_client_id == buyer


@then("exactly 1 report is stored for the trade")
def step_then_one_row(context):
    assert list(context.repo.rows) == [context.payload["trade_id"]]


@then("{count:d} deliveries are counted as duplicates")
def step_then_duplicates(context, count):
    assert context.outcomes.count("DUPLICATE") == count
