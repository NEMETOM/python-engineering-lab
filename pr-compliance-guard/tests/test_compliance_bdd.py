# pr-compliance-guard/tests/test_compliance_bdd.py

import pytest
from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers

from compliance.engine import ComplianceEngine
from compliance.config import load_config


# Load feature file
scenarios("features/compliance.feature")


# -------------------------------------------------
# Config fixture (robust path resolution)
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]


#@pytest.fixture(params=["default.yaml", "relaxed.yaml"])
#def config(request):
#    config_path = BASE_DIR / "config" / request.param
#    return load_config(config_path)

@pytest.fixture
def config():
    return load_config("config/default.yaml")


@pytest.fixture
def engine(config):
    return ComplianceEngine(config)


@pytest.fixture
def pr_context():
    return {}


# -------------------------
# GIVEN steps
# -------------------------

@given(parsers.parse('branch "{branch_name}"'))
def given_branch(pr_context, branch_name):
    pr_context["branch"] = branch_name


@given(parsers.parse('commit message "{commit_message}"'))
def given_commit_message(pr_context, commit_message):
    pr_context["commit"] = commit_message


@given(parsers.parse('PR title "{title}"'))
def given_pr_title(pr_context, title):
    pr_context["title"] = title


# -------------------------
# WHEN step
# -------------------------

@when("compliance is evaluated")
def when_compliance_is_evaluated(pr_context, engine):
    result = engine.evaluate(
        branch=pr_context["branch"],
        commit=pr_context["commit"],
        title=pr_context["title"],
    )
    pr_context["result"] = result


# -------------------------
# THEN steps
# -------------------------

@then("result should be compliant")
def then_result_should_be_compliant(pr_context):
    result = pr_context["result"]

    assert result["compliant"] is True
    assert result["branch"] is True
    assert result["commit"] is True
    assert result["jira"] is True


@then("result should fail")
def then_result_should_fail(pr_context):
    result = pr_context["result"]

    assert result["compliant"] is False
    assert any(value is False for key, value in result.items() if key != "compliant")
