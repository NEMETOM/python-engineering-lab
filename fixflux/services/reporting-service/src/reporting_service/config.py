import os
from pathlib import Path

import yaml

INPUT_TOPIC = "trades"
GROUP_ID = "reporting-service"

METRICS_PORT = int(os.getenv("REPORTING_METRICS_PORT", "8012"))

# RTS 1 Art. 14(1)(a): post-trade information is published "as close to
# real-time as is technically possible and in any case within one minute".
PUBLICATION_DEADLINE_SECONDS = float(os.getenv("REPORTING_DEADLINE_SECONDS", "60"))

# fix-replay rewrites client IDs to RPL-<run>-<original>; stripping that prefix
# lets replayed trades resolve to the original participant's reference data.
CLIENT_ALIAS_PATTERN = os.getenv("REPORTING_CLIENT_ALIAS_PATTERN", r"^RPL-[^-]+-")

# Postgres unavailable: retry the same report with capped exponential backoff
# rather than skipping it - a lagging consumer is visible (KafkaConsumerLagHigh),
# a silently dropped regulatory report is not.
DB_RETRY_MAX_BACKOFF_SECONDS = float(os.getenv("REPORTING_DB_RETRY_MAX_BACKOFF", "30"))

# Password for the read-only Grafana role (see public_view.py). Unset means the
# role is never created - there is deliberately no default credential.
GRAFANA_READER_PASSWORD = os.getenv("GRAFANA_DB_READER_PASSWORD") or None

# Priority order (same scheme as compliance-service's policy file):
# 1. Explicit path argument (tests / programmatic callers)
# 2. REPORTING_REFERENCE_DATA_PATH env var
# 3. /app/reference/ - where the Dockerfile copies the file
# 4. Source-relative path - works with pip install -e . in local development
_DOCKER_DEFAULT = Path("/app/reference/reference_data.yaml")
_SOURCE_DEFAULT = (
    Path(__file__).parent.parent.parent / "reference" / "reference_data.yaml"
)


def load_reference_data(path: Path | None = None) -> dict:
    if path is not None:
        data_path = path
    elif env := os.getenv("REPORTING_REFERENCE_DATA_PATH"):
        data_path = Path(env)
    elif _DOCKER_DEFAULT.exists():
        data_path = _DOCKER_DEFAULT
    else:
        data_path = _SOURCE_DEFAULT
    with open(data_path) as f:
        return yaml.safe_load(f)
