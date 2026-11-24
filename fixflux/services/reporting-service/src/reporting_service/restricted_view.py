"""Restricted, read-only view of regulatory_reports for the regulator dashboard.

Carries the transaction-reporting fields (RTS 22 style) that must never reach
the public view (public_view.py): buyer/seller LEI, trading capacity, CFI code,
and the unredacted status reason. Its own role can SELECT this view and nothing
else, and Grafana reaches it through a separate datasource (postgres-regulator)
used only by the dashboards in the Restricted folder.

Parties are identified by LEI, as in a transaction report. Internal client IDs
are left out; they appear only inside INCOMPLETE reasons ("no LEI for buyer
VOL_B0001"), which is exactly what whoever fixes the reference data needs.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from reporting_service.public_view import grant_reader

RESTRICTED_VIEW_NAME = "regulatory_reports_restricted"
REGULATOR_ROLE = "grafana_regulator"

# Only APPEND to this tuple, for the same reason as PUBLIC_COLUMNS:
# CREATE OR REPLACE VIEW rejects removed or reordered columns.
RESTRICTED_COLUMNS = (
    "trade_id",
    "symbol",
    "asset_class",
    "cfi_code",
    "price",
    "price_currency",
    "quantity",
    "trading_timestamp",
    "reporting_timestamp",
    "buyer_lei",
    "seller_lei",
    "buyer_trading_capacity",
    "seller_trading_capacity",
    "status",
    "status_reason",
    "publication_latency_ms",
    "deadline_breached",
)

RESTRICTED_VIEW_SQL = (
    f"CREATE OR REPLACE VIEW {RESTRICTED_VIEW_NAME} AS "
    f"SELECT {', '.join(RESTRICTED_COLUMNS)} FROM regulatory_reports"
)


def ensure_restricted_view(engine: Engine, password: str | None) -> bool:
    """Create or refresh the view, and the regulator role if a password is set.

    Idempotent, so it runs on every start. Returns True if the role was
    created or updated. Without a password the role is left alone: no default
    credential is ever created.
    """
    with engine.begin() as conn:
        conn.execute(text(RESTRICTED_VIEW_SQL))
        if not password:
            return False
        grant_reader(conn, REGULATOR_ROLE, password, RESTRICTED_VIEW_NAME)
    return True
