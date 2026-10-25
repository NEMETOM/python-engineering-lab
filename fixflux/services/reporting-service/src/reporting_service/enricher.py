import re
from collections.abc import Callable
from datetime import UTC, datetime

from reporting_service import config
from reporting_service.schemas import RegulatoryTradeReport, TradeEvent
from reporting_service.schemas.regulatory_report import ReportStatus


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class ReportEnricher:
    """Turns a trade into a RegulatoryTradeReport using static reference data.

    Status precedence: an out-of-scope instrument is NOT_REPORTABLE regardless
    of anything else (there is nothing to publish); otherwise any missing
    reference data or execution time makes the report INCOMPLETE. Missing data
    is never defaulted - an INCOMPLETE row is the signal to fix reference data.
    """

    def __init__(
        self,
        reference_data: dict,
        alias_pattern: str = config.CLIENT_ALIAS_PATTERN,
        deadline_seconds: float = config.PUBLICATION_DEADLINE_SECONDS,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.participants: dict = reference_data.get("participants") or {}
        self.instruments: dict = reference_data.get("instruments") or {}
        self.alias = re.compile(alias_pattern) if alias_pattern else None
        self.deadline_ms = deadline_seconds * 1000
        self.clock = clock

    def _participant(self, client_id: str) -> dict | None:
        if self.alias:
            client_id = self.alias.sub("", client_id, count=1)
        return self.participants.get(client_id)

    def enrich(self, trade: TradeEvent) -> RegulatoryTradeReport:
        now = self.clock()
        instrument = self.instruments.get(trade.symbol)
        buyer = self._participant(trade.buy_client_id)
        seller = self._participant(trade.sell_client_id)

        traded_at = _utc(trade.timestamp) if trade.timestamp else None
        latency_ms = (
            int((now - traded_at).total_seconds() * 1000) if traded_at else None
        )

        status: ReportStatus
        if instrument is not None and not instrument.get("mifid_in_scope", False):
            status = "NOT_REPORTABLE"
            reason = instrument.get("out_of_scope_reason") or "instrument out of scope"
        else:
            problems = []
            if instrument is None:
                problems.append(f"no reference data for instrument {trade.symbol}")
            if buyer is None:
                problems.append(f"no LEI for buyer {trade.buy_client_id}")
            if seller is None:
                problems.append(f"no LEI for seller {trade.sell_client_id}")
            if traded_at is None:
                problems.append("trade has no execution timestamp")
            status = "INCOMPLETE" if problems else "REPORTABLE"
            reason = "; ".join(problems) or None

        instrument = instrument or {}
        buyer = buyer or {}
        seller = seller or {}
        return RegulatoryTradeReport(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            price=trade.price,
            price_currency=instrument.get("currency"),
            quantity=trade.quantity,
            trading_timestamp=traded_at,
            reporting_timestamp=now,
            buyer_client_id=trade.buy_client_id,
            seller_client_id=trade.sell_client_id,
            buyer_lei=buyer.get("lei"),
            seller_lei=seller.get("lei"),
            buyer_trading_capacity=buyer.get("trading_capacity"),
            seller_trading_capacity=seller.get("trading_capacity"),
            cfi_code=instrument.get("cfi_code"),
            asset_class=instrument.get("asset_class"),
            status=status,
            status_reason=reason,
            publication_latency_ms=latency_ms,
            deadline_breached=latency_ms is not None and latency_ms > self.deadline_ms,
        )
