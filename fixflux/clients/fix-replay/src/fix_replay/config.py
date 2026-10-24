import os

INPUT_TOPIC = "raw_orders"
REPORTS_TOPIC = "execution_reports"

MATCHING_ENGINE_METRICS_URL = os.getenv(
    "MATCHING_ENGINE_METRICS_URL", "http://localhost:8003/metrics"
)

DEFAULT_RATE = 20.0  # orders/second
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_SETTLE_S = 5.0


def client_prefix(run_id: str) -> str:
    return f"RPL-{run_id}-"
