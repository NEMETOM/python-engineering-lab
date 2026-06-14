"""
Quick smoke-test for the local PostgreSQL connection.

Run from anywhere inside the repo:
    python scripts/test_db_connection.py

Steps:
  1. Connect to the database defined in shared/config/config.yaml
  2. Create the 'trades' table if it doesn't exist
  3. Insert a test trade record
  4. Read it back
  5. Delete it (clean up)
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "services" / "trade-store" / "src"))

from shared.infrastructure.db import Base, SessionLocal, engine  # noqa: E402
from shared.observability.log_config import configure_logging, get_logger  # noqa: E402
from trade_store.models import TradeModel  # noqa: E402

configure_logging()
logger = get_logger(__name__)

TEST_TRADE_ID = "TEST-CONNECTIVITY-001"


def run() -> None:
    logger.info("=== DB connectivity test started ===")

    logger.info("Connecting to database...")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Connected OK")

    logger.info("Creating tables if missing...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables OK")

    session = SessionLocal()
    try:
        leftover = session.get(TradeModel, TEST_TRADE_ID)
        if leftover:
            logger.warning(
                "Leftover record found from a previous interrupted run - "
                "trade_id=%s, symbol=%s, price=%s, qty=%s, inserted_at=%s",
                leftover.trade_id, leftover.symbol,
                leftover.price, leftover.quantity, leftover.timestamp,
            )
            session.delete(leftover)
            session.commit()
            logger.info("Leftover record removed OK")

        logger.info("Inserting test record  trade_id=%s ...", TEST_TRADE_ID)
        session.add(TradeModel(
            trade_id=TEST_TRADE_ID,
            symbol="TEST",
            buy_order_id="B-TEST",
            sell_order_id="S-TEST",
            price=1.0,
            quantity=1,
            timestamp=datetime.now(timezone.utc),
        ))
        session.commit()
        logger.info("Insert OK")

        logger.info("Reading back...")
        found = session.get(TradeModel, TEST_TRADE_ID)
        assert found is not None, "Record not found after insert"
        logger.info(
            "Read OK - trade_id=%s, symbol=%s, price=%s, qty=%s",
            found.trade_id, found.symbol, found.price, found.quantity,
        )

        logger.info("Running: SELECT * FROM trades")
        all_trades = session.query(TradeModel).all()
        logger.info("Row count: %d", len(all_trades))
        for row in all_trades:
            logger.info(
                "  trade_id=%-30s symbol=%-10s buy_order_id=%-10s "
                "sell_order_id=%-10s price=%-10s qty=%-5s timestamp=%s",
                row.trade_id, row.symbol, row.buy_order_id,
                row.sell_order_id, row.price, row.quantity, row.timestamp,
            )

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    logger.info("=== All checks passed ===")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logger.error("DB connectivity test FAILED: %s", exc)
        sys.exit(1)
