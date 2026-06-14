from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ViolationResponse(BaseModel):
    id: UUID
    rule_name: str
    rule_category: str
    client_id: str | None
    symbol: str | None
    order_id: str | None
    severity: str
    description: str
    status: str
    risk_contribution: float | None
    detected_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None


class ViolationStatusUpdate(BaseModel):
    status: str
    reviewed_by: str | None = None


class RiskScoreResponse(BaseModel):
    client_id: str
    risk_score: float
    violation_count: int
    last_violation_at: datetime | None
    is_high_risk: bool
    updated_at: datetime


class AuditEntryResponse(BaseModel):
    id: int
    event_type: str
    client_id: str | None
    entity_id: str | None
    entity_type: str | None
    action: str
    payload: dict[str, Any]
    checksum: str | None
    recorded_at: datetime
