from fastapi import APIRouter, HTTPException, Query

from compliance_service.repository.violation_repository import ViolationRepository

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("")
def list_risk_scores(limit: int = Query(default=100, ge=1, le=1000)):
    """Return all clients sorted by risk score descending."""
    repo = ViolationRepository()
    return repo.list_risk_scores(limit=limit)


@router.get("/{client_id}")
def get_client_risk(client_id: str):
    """Return the current risk profile for a specific client."""
    repo = ViolationRepository()
    score = repo.get_risk_score(client_id)
    if not score:
        raise HTTPException(
            status_code=404, detail=f"No risk record found for client '{client_id}'"
        )
    return score
