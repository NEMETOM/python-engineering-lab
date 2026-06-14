from fastapi import APIRouter, Query

from compliance_service.repository.audit_repository import AuditRepository

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_trail(
    client_id: str | None = None,
    event_type: str | None = Query(
        default=None,
        description="order_received | violation_detected | status_updated",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Return the compliance audit trail, most recent first. Records are immutable."""
    repo = AuditRepository()
    return repo.list_entries(client_id=client_id, event_type=event_type, limit=limit)
