"""Public, read-only view of regulatory_reports for Grafana and the post-trade feed.

The view carries only RTS 1 post-trade transparency fields (no LEIs, client
IDs or trading capacity), and each reader role can SELECT from the view and
nothing else. Grafana's Explore lets any Editor run arbitrary SQL through a
datasource, and the feed is an unauthenticated HTTP endpoint, so the database
role - not the dashboard or the API code - is what limits what a compromised
reader could see.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

VIEW_NAME = "regulatory_reports_public"
READER_ROLE = "grafana_reader"
# reporting-api's role for the public post-trade feed (api/main.py).
FEED_READER_ROLE = "public_feed_reader"

# Never add buyer_*/seller_* columns, LEIs or capacity here: RTS 1 publication
# must not identify the counterparties.
# Only APPEND to this tuple: CREATE OR REPLACE VIEW rejects removed or
# reordered columns, which would stop reporting-service at startup. To drop a
# column, DROP VIEW first (Grafana's grant must then be re-applied - the next
# start does that).
PUBLIC_COLUMNS = (
    "trade_id",
    "symbol",
    "asset_class",
    "price",
    "price_currency",
    "quantity",
    "trading_timestamp",
    "reporting_timestamp",
    "status",
    "publication_latency_ms",
    "deadline_breached",
)

# INCOMPLETE reasons name the client with the missing LEI, so they are
# replaced; NOT_REPORTABLE reasons describe the instrument and are kept.
_PUBLIC_REASON = (
    "CASE WHEN status = 'INCOMPLETE' "
    "THEN 'missing reference data (details restricted)' "
    "ELSE status_reason END AS reason"
)

VIEW_SQL = (
    f"CREATE OR REPLACE VIEW {VIEW_NAME} AS "
    f"SELECT {', '.join(PUBLIC_COLUMNS)}, {_PUBLIC_REASON} "
    "FROM regulatory_reports"
)


# Limits on what a stolen reader password can do even with a valid login: no
# writes even if a grant is ever widened by mistake, no query long enough to
# starve the 2-vCPU droplet, and no connection flood. Grafana's datasource uses
# 2 connections (maxOpenConns in postgres_public.yml), reporting-api's pool 2.
READER_CONNECTION_LIMIT = 3
READER_SETTINGS = (
    ("default_transaction_read_only", "on"),
    ("statement_timeout", "'5s'"),
    ("idle_in_transaction_session_timeout", "'30s'"),
)


def _quote_literal(value: str) -> str:
    # CREATE/ALTER ROLE ... PASSWORD can't take a bind parameter.
    return "'" + value.replace("'", "''") + "'"


def ensure_public_view(engine: Engine, readers: dict[str, str | None]) -> list[str]:
    """Create or refresh the view, and each reader role that has a password.

    `readers` maps role name to password. Idempotent, so it runs on every
    start. Returns the roles created or updated. A role without a password is
    left alone: no default credential is ever created.
    """
    ready = []
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL))
        for role, password in readers.items():
            if not password:
                continue
            exists = conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
                {"name": role},
            ).scalar()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(
                text(
                    f"{verb} ROLE {role} LOGIN "
                    f"CONNECTION LIMIT {READER_CONNECTION_LIMIT} "
                    f"PASSWORD {_quote_literal(password)}"
                )
            )
            for setting, value in READER_SETTINGS:
                conn.execute(text(f"ALTER ROLE {role} SET {setting} = {value}"))
            conn.execute(text(f"GRANT SELECT ON {VIEW_NAME} TO {role}"))
            ready.append(role)
    return ready
