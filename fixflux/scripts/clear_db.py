"""
Clears all trade and compliance data from the database.

Run before each test session to start with a clean slate:
    python scripts/clear_db.py

Skip the confirmation prompt (e.g. in CI or shell aliases):
    python scripts/clear_db.py --force

Tables cleared:
    trades                   - matched trade records (trade-store)
    compliance_violations    - compliance rule violations
    client_risk_scores       - per-client risk scores
    compliance_audit_trail   - immutable audit trail

PostgreSQL sequences (e.g. compliance_audit_trail.id) are reset to 1.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# ── Path setup ────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from shared.config._loader import build_db_url  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────
_TABLES = [
    "compliance_audit_trail",
    "compliance_violations",
    "client_risk_scores",
    "trades",
]

# ── Helpers ───────────────────────────────────────────────────────────────────
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _count(conn, table: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


def _print_counts(conn, label: str) -> None:
    print(f"\n{_BOLD}{label}{_RESET}")
    for table in _TABLES:
        try:
            n = _count(conn, table)
            colour = _YELLOW if n > 0 else _GREEN
            print(f"  {colour}{table:<35} {n:>6} row(s){_RESET}")
        except Exception:
            print(f"  {_RED}{table:<35} (table not found - run the stack first){_RESET}")


def run(force: bool) -> None:
    engine = create_engine(build_db_url())

    with engine.connect() as conn:
        _print_counts(conn, "Current row counts:")

        if not force:
            print(
                f"\n{_YELLOW}This will permanently delete ALL rows from the tables above.{_RESET}"
            )
            answer = input("Type 'yes' to continue: ").strip().lower()
            if answer != "yes":
                print("Aborted.")
                sys.exit(0)

        print(f"\n{_BOLD}Clearing tables...{_RESET}")
        for table in _TABLES:
            try:
                conn.execute(
                    text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                )
                print(f"  {_GREEN}TRUNCATED{_RESET}  {table}")
            except Exception as exc:
                print(f"  {_RED}FAILED{_RESET}     {table}  ({exc})")

        conn.commit()
        _print_counts(conn, "Row counts after clear:")

    print(f"\n{_GREEN}{_BOLD}Done. Database is clean.{_RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    args = parser.parse_args()
    run(force=args.force)
