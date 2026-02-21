#pr-compliance-guard/tests/test_engine_from_json.py

import json
import pytest
from compliance.engine import ComplianceEngine
from compliance.config import load_config


@pytest.fixture
def engine():
    config = load_config("config/default.yaml")
    return ComplianceEngine(config)


@pytest.mark.parametrize(
    "json_file, expected",
    [
        ("tests/data/valid_pr.json", True),
        ("tests/data/invalid_pr.json", False),
    ],
)
def test_engine_with_json_inputs(engine, json_file, expected):
    with open(json_file) as f:
        data = json.load(f)

    result = engine.evaluate(
        branch=data["branch"],
        commit=data["commit"],
        title=data["title"],
    )

    assert result["compliant"] is expected
