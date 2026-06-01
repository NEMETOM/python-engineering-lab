import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID

from compliance_service.infrastructure.db import Base


class ComplianceViolation(Base):
    __tablename__ = "compliance_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name = Column(String(100), nullable=False)
    rule_category = Column(String(50), nullable=False)
    client_id = Column(String(100))
    symbol = Column(String(20))
    order_id = Column(String(100))
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    raw_event = Column(JSON, nullable=False)
    status = Column(String(20), default="OPEN")
    risk_contribution = Column(Float)
    detected_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(100))


class ClientRiskScore(Base):
    __tablename__ = "client_risk_scores"

    client_id = Column(String(100), primary_key=True)
    risk_score = Column(Float, nullable=False, default=0.0)
    violation_count = Column(Integer, nullable=False, default=0)
    last_violation_at = Column(DateTime(timezone=True))
    is_high_risk = Column(Boolean, default=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ComplianceAuditTrail(Base):
    __tablename__ = "compliance_audit_trail"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)
    client_id = Column(String(100))
    entity_id = Column(String(100))
    entity_type = Column(String(50))
    action = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    checksum = Column(String(64))
    recorded_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
