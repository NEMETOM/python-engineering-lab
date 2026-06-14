from fastapi import APIRouter, HTTPException, Query

from compliance_service.repository.violation_repository import ViolationRepository
from compliance_service.schemas.violation import ViolationStatusUpdate
from compliance_service.utils.logger import get_logger

router = APIRouter(prefix="/violations", tags=["violations"])
logger = get_logger(__name__)

_VALID_STATUSES = {"OPEN", "REVIEWED", "DISMISSED", "ESCALATED"}
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


@router.get("")
def list_violations(
    client_id: str | None = None,
    severity: str | None = Query(
        default=None, description="LOW | MEDIUM | HIGH | CRITICAL"
    ),
    status: str | None = Query(
        default=None, description="OPEN | REVIEWED | DISMISSED | ESCALATED"
    ),
    rule_name: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    if severity and severity.upper() not in _VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity. Choose from: {_VALID_SEVERITIES}",
        )
    if status and status.upper() not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"Invalid status. Choose from: {_VALID_STATUSES}"
        )
    repo = ViolationRepository()
    return repo.list_violations(
        client_id=client_id,
        severity=severity,
        status=status,
        rule_name=rule_name,
        limit=limit,
    )


@router.get("/{violation_id}")
def get_violation(violation_id: str):
    repo = ViolationRepository()
    violation = repo.get_by_id(violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violation


@router.patch("/{violation_id}/status")
def update_violation_status(violation_id: str, update: ViolationStatusUpdate):
    if update.status.upper() not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"Invalid status. Choose from: {_VALID_STATUSES}"
        )
    repo = ViolationRepository()
    updated = repo.update_status(violation_id, update.status, update.reviewed_by)
    if not updated:
        raise HTTPException(status_code=404, detail="Violation not found")
    logger.info(
        f"Violation {violation_id} status -> {update.status} by {update.reviewed_by}"
    )
    return {"id": violation_id, "status": update.status.upper()}
