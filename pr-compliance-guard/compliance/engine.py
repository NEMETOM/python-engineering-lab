#pr-compliance-guard/compliance/engine.py
from compliance.rules import branch_is_valid, commit_is_valid, pr_has_jira


class ComplianceEngine:
    def __init__(self, config: dict):
        self.config = config

    def evaluate(self, branch: str, commit: str, title: str) -> dict:
        results = {}

        results["branch"] = branch_is_valid(
            branch, self.config["branch"]["pattern"]
        )

        results["commit"] = commit_is_valid(
            commit, self.config["commit"]["forbidden_words"]
        )

        if self.config["pr"]["require_jira"]:
            results["jira"] = pr_has_jira(
                title, self.config["pr"]["jira_pattern"]
            )
        else:
            results["jira"] = True

        results["compliant"] = all(results.values())
        return results
