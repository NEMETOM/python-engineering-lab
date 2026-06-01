from pathlib import Path

import yaml

_DEFAULT_POLICY_PATH = (
    Path(__file__).parent.parent.parent / "policies" / "compliance_policies.yaml"
)


def load_policies(path: Path | None = None) -> dict:
    policy_path = path or _DEFAULT_POLICY_PATH
    with open(policy_path) as f:
        return yaml.safe_load(f)
