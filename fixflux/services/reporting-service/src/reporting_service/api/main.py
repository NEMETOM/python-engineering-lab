"""reporting-api: the RTS 1 public post-trade feed over HTTP.

Unauthenticated by design (post-trade transparency data is public), so the
safety comes from below: the engine connects as public_feed_reader, which can
only SELECT from regulatory_reports_public, read-only, with a 5s statement
timeout and 3 connections (public_view.py). This module deliberately doesn't
import shared.infrastructure.db, whose engine connects as fixuser.
"""

import csv
import io
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from reporting_service import config
from reporting_service.feed import FEED_COLUMNS, PostTradeFeed
from reporting_service.utils.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="FixFlux Post-Trade Feed (RTS 1)")

# Cells starting with one of these are run as formulas by spreadsheet apps.
# Symbols come from injected FIX messages, so they are untrusted text.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class FeedUnavailable(Exception):
    pass


@lru_cache
def get_feed() -> PostTradeFeed:
    if not config.FEED_DATABASE_URL:
        raise FeedUnavailable("PUBLIC_FEED_DATABASE_URL is not set")
    # Pool stays under the role's CONNECTION LIMIT 3.
    engine = create_engine(
        config.FEED_DATABASE_URL, pool_size=2, max_overflow=0, pool_pre_ping=True
    )
    return PostTradeFeed(engine, delay_seconds=config.FEED_DELAY_SECONDS)


def _feed() -> PostTradeFeed:
    try:
        return get_feed()
    except FeedUnavailable as exc:
        logger.error(f"post_trade_feed | unavailable reason={exc}")
        raise HTTPException(503, "post-trade feed temporarily unavailable") from exc


def _utc_z(value: object) -> object:
    # "...Z", not "+00:00": a "+" pasted into a URL arrives as a space, so a
    # copied next_since cursor would be rejected.
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return value


def _public(trades: list[dict]) -> list[dict]:
    return [{k: _utc_z(v) for k, v in t.items()} for t in trades]


def _csv_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _to_csv(trades: list[dict]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FEED_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for trade in trades:
        writer.writerow({k: _csv_cell(v) for k, v in trade.items()})
    return out.getvalue()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/post-trade")
def post_trade(
    symbol: str | None = Query(None, pattern=r"^[A-Za-z0-9._-]{1,16}$"),
    since: datetime | None = Query(
        None, description="Only trades published after this time (ISO 8601)"
    ),
    limit: int = Query(config.FEED_DEFAULT_LIMIT, ge=1, le=config.FEED_MAX_LIMIT),
    format: Literal["json", "csv"] = "json",
    feed: PostTradeFeed = Depends(_feed),
):
    if since is not None and since.tzinfo is None:
        raise HTTPException(422, "since needs a timezone, e.g. 2026-11-22T10:00:00Z")
    symbol = symbol.upper() if symbol else None
    try:
        trades = _public(feed.fetch(symbol, since, limit))
    except SQLAlchemyError as exc:
        logger.error(f"post_trade_feed | query failed reason={exc}")
        raise HTTPException(503, "post-trade feed temporarily unavailable") from exc
    logger.info(
        f"post_trade_feed | symbol={symbol} since={since} limit={limit} "
        f"format={format} rows={len(trades)}"
    )
    if format == "csv":
        return Response(_to_csv(trades), media_type="text/csv")
    next_since = trades[-1]["reporting_timestamp"] if trades else _utc_z(since)
    return {"count": len(trades), "next_since": next_since, "trades": trades}
