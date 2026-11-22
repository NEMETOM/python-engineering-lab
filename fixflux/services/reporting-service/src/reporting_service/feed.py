"""RTS 1 public post-trade feed: reads regulatory_reports_public, nothing else.

Only REPORTABLE trades are published. NOT_REPORTABLE instruments are out of
scope (nothing to publish) and INCOMPLETE reports are still waiting on
reference data.

`since` filters on reporting_timestamp (when the trade was published), not on
the execution time: a client polling with the last row's reporting_timestamp
can't miss a trade that executed earlier but was published later.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine

from reporting_service.public_view import VIEW_NAME

# A subset of public_view.PUBLIC_COLUMNS, in output order. Status, reason and
# latency describe our own reporting pipeline, not the trade.
FEED_COLUMNS = (
    "trade_id",
    "symbol",
    "asset_class",
    "price",
    "price_currency",
    "quantity",
    "trading_timestamp",
    "reporting_timestamp",
)

_SELECT = f"SELECT {', '.join(FEED_COLUMNS)} FROM {VIEW_NAME}"


def build_query(symbol: str | None, since: datetime | None, limit: int) -> str:
    """With `since`: the oldest `limit` trades published after it (next page).
    Without: the latest `limit` trades. Rows always come back oldest first."""
    where = ["status = 'REPORTABLE'", "reporting_timestamp <= :cutoff"]
    if symbol is not None:
        where.append("symbol = :symbol")
    if since is not None:
        where.append("reporting_timestamp > :since")
    order = "ASC" if since is not None else "DESC"
    return (
        f"{_SELECT} WHERE {' AND '.join(where)} "
        f"ORDER BY reporting_timestamp {order}, trade_id {order} LIMIT :limit"
    )


class PostTradeFeed:

    def __init__(
        self,
        engine: Engine,
        delay_seconds: float = 0,
        clock=lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.delay = timedelta(seconds=delay_seconds)
        self.clock = clock

    def fetch(
        self, symbol: str | None, since: datetime | None, limit: int
    ) -> list[dict]:
        params: dict = {"cutoff": self.clock() - self.delay, "limit": limit}
        if symbol is not None:
            params["symbol"] = symbol
        if since is not None:
            params["since"] = since
        with self.engine.connect() as conn:
            rows = conn.execute(text(build_query(symbol, since, limit)), params)
            trades = [dict(r._mapping) for r in rows]
        return trades if since is not None else trades[::-1]
