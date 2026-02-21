# pr-compliance-guard/tests/test_engine.py

import pytest
from compliance.engine import ComplianceEngine


@pytest.fixture
def config():
    return {
        "branch": {"pattern": r"^feature/COM-\d+-.*"},
        "commit": {"forbidden_words": ["WIP", "fixup"]},
        "pr": {
            "require_jira": True,
            "jira_pattern": r"COM-\d+",
        },
    }


@pytest.fixture
def engine(config):
    return ComplianceEngine(config)


def test_valid_pr(engine):
    result = engine.evaluate(
        branch="feature/COM-123-test",
        commit="COM-123 add feature",
        title="COM-123 Add feature",
    )
    assert result["compliant"] is True


def test_invalid_branch(engine):
    result = engine.evaluate(
        branch="random-branch",
        commit="COM-123 add feature",
        title="COM-123 Add feature",
    )
    assert result["compliant"] is False