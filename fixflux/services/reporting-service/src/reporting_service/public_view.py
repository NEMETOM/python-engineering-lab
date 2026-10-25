"""Public, read-only view of regulatory_reports for Grafana.

The view carries only RTS 1 post-trade transparency fields (no LEIs, client
IDs or trading capacity), and the reader role can SELECT from the view and
nothing else. Grafana's Explore lets any Editor run arbitrary SQL through a
datasource, so the database role - not the dashboard - is what limits what a
compromised Grafana could read.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

VIEW_NAME = "regulatory_reports_public"
READER_ROLE = "grafana_reader"

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


def _quote_literal(value: str) -> str:
    # CREATE/ALTER ROLE ... PASSWORD can't take a bind parameter.
    return "'" + value.replace("'", "''") + "'"


def ensure_public_view(engine: Engine, reader_password: str | None) -> bool:
    """Create or refresh the view, and the reader role when a password is set.

    Idempotent, so it runs on every start. Returns True if the role was
    created or updated. Without a password the role is left alone: no default
    credential is ever created.
    """
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL))
        if not reader_password:
            return False
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
            {"name": READER_ROLE},
        ).scalar()
        verb = "ALTER" if exists else "CREATE"
        conn.execute(
            text(
                f"{verb} ROLE {READER_ROLE} LOGIN "
                f"PASSWORD {_quote_literal(reader_password)}"
            )
        )
        conn.execute(text(f"GRANT SELECT ON {VIEW_NAME} TO {READER_ROLE}"))
    return True
