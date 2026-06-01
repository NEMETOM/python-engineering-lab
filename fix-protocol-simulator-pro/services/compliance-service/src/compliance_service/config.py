import os
from pathlib import Path

import yaml

# Priority order:
# 1. Explicit path argument (tests / programmatic callers)
# 2. COMPLIANCE_POLICY_PATH env var (Kubernetes ConfigMap mount, custom paths)
# 3. /app/policies/ - where the Dockerfile copies the file after pip install .
# 4. Source-relative path - works with pip install -e . in local development
_DOCKER_DEFAULT = Path("/app/policies/compliance_policies.yaml")
_SOURCE_DEFAULT = (
    Path(__file__).parent.parent.parent / "policies" / "compliance_policies.yaml"
)


def load_policies(path: Path | None = None) -> dict:
    if path is not None:
        policy_path = path
    elif env := os.getenv("COMPLIANCE_POLICY_PATH"):
        policy_path = Path(env)
    elif _DOCKER_DEFAULT.exists():
        policy_path = _DOCKER_DEFAULT
    else:
        policy_path = _SOURCE_DEFAULT
    with open(policy_path) as f:
        return yaml.safe_load(f)
