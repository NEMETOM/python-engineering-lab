from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Violation:
    rule_name: str
    rule_category: str
    severity: Severity
    description: str
    raw_event: dict[str, Any]
    client_id: str | None = None
    symbol: str | None = None
    order_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Rule(ABC):
    """Base class for all compliance and surveillance rules."""

    category: str = "compliance"

    def __init__(self, config: dict):
        self.config = config
        self.enabled: bool = config.get("enabled", True)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def check(self, event: dict[str, Any]) -> Violation | None: ...
