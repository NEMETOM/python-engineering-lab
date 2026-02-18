# pr-compliance-guard/tests/test_engine.py

import pytest
from compliance.engine import evaluate_pr


def test_rejects_pr_without_description():
    pr = {
        "title": "Add new feature",
        "description": "",
        "approvals": 2,
        "changed_files": 3,
    }

    result = evaluate_pr(pr)

    assert result["approved"] is False
    assert "Missing description" in result["violations"]


def test_rejects_pr_with_no_approvals():
    pr = {
        "title": "Fix bug",
        "description": "Fixes issue with login",
        "approvals": 0,
        "changed_files": 2,
    }

    result = evaluate_pr(pr)

    assert result["approved"] is False
    assert "Not enough approvals" in result["violations"]


def test_rejects_pr_with_too_many_changed_files():
    pr = {
        "title": "Refactor system",
        "description": "Large refactor",
        "approvals": 2,
        "changed_files": 50,
    }

    result = evaluate_pr(pr)

    assert result["approved"] is False
    assert "Too many files changed" in result["violations"]


def test_approves_valid_pr():
    pr = {
        "title": "Small improvement",
        "description": "Improves logging clarity",
        "approvals": 2,
        "changed_files": 4,
    }

    result = evaluate_pr(pr)

    assert result["approved"] is True
    assert result["violations"] == []
