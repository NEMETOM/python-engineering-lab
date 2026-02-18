import argparse
import json
from compliance.engine import ComplianceEngine
from compliance.config import load_config


def main():
    parser = argparse.ArgumentParser(description="PR Compliance Checker")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--input", required=True, help="Path to PR JSON file")

    args = parser.parse_args()

    config = load_config(args.config)
    engine = ComplianceEngine(config)

    with open(args.input) as f:
        data = json.load(f)

    result = engine.evaluate(
        branch=data["branch"],
        commit=data["commit"],
        title=data["title"],
    )

    print(json.dumps(result, indent=2))

    if not result["compliant"]:
        exit(1)
