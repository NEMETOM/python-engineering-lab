# tests/test_engine_from_json.py

import json
import pytest
from compliance.engine import ComplianceEngine
from compliance.config import load_config

@pytest.fixture
def default_config():
    """Load the default config once for all tests."""
    return load_config("config/default.yaml")

@pytest.mark.parametrize(
    "json_file, override_config, expected",
    [
        ("tests/data/valid_pr.json", None, True),  # normal PR
        ("tests/data/invalid_pr.json", None, False),  # invalid branch/commit
        ("tests/data/no_jira_pr.json", {"pr": {"require_jira": False}}, True),  # exercise else branch
    ],
)
def test_engine_with_json_inputs(default_config, json_file, override_config, expected):
    # Load test input from JSON file
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Prepare config
    config = default_config.copy()
    if override_config:
        for section, updates in override_config.items():
            config[section].update(updates)

    engine = ComplianceEngine(config)

    result = engine.evaluate(
        branch=data["branch"],
        commit=data["commit"],
        title=data["title"]
    )

    assert result["compliant"] is expected
    