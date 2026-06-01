from typing import Any

from compliance_service.rules.base import Rule, Violation
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)


class RulesEngine:
    """Evaluates a list of rules against an event and returns all violations found."""

    def __init__(self, rules: list[Rule]):
        self.rules = [r for r in rules if r.enabled]
        logger.info(f"RulesEngine initialised with {len(self.rules)} active rule(s)")

    def evaluate(self, event: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        for rule in self.rules:
            try:
                violation = rule.check(event)
                if violation:
                    violations.append(violation)
                    logger.warning(
                        f"VIOLATION [{violation.severity.value}] "
                        f"{violation.rule_name}: {violation.description}"
                    )
            except Exception as exc:
                logger.error(
                    f"Rule {rule.name} raised an exception: {exc}", exc_info=True
                )
        return violations
