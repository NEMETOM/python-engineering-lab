from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from compliance_service.config import load_policies
from compliance_service.repository.rule_override_repository import (
    RuleOverrideRepository,
)
from compliance_service.rules.catalog import RULE_CATALOG, RULE_IDS
from compliance_service.schemas.rule_override import RuleToggleRequest
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["admin"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _default_enabled(policies: dict, rule_id: str, category: str) -> bool:
    section = policies.get(category, {})
    return bool(section.get(rule_id, {}).get("enabled", True))


def _effective_rules() -> list[dict]:
    policies = load_policies()
    overrides = RuleOverrideRepository().get_all()
    rules = []
    for entry in RULE_CATALOG:
        rule_id = entry["rule_id"]
        default_enabled = _default_enabled(policies, rule_id, entry["category"])
        rules.append(
            {
                **entry,
                "enabled": overrides.get(rule_id, default_enabled),
                "overridden": rule_id in overrides,
            }
        )
    return rules


@router.get("/admin/compliance", response_class=HTMLResponse)
def admin_compliance_page(request: Request):
    return templates.TemplateResponse(
        request,
        "admin_compliance.html",
        {"rules": _effective_rules(), "active_tab": "compliance"},
    )


@router.post("/api/compliance/toggle")
def toggle_rule(body: RuleToggleRequest):
    if body.rule_id not in RULE_IDS:
        raise HTTPException(
            status_code=404, detail=f"Unknown rule_id: {body.rule_id!r}"
        )
    RuleOverrideRepository().upsert(body.rule_id, body.enabled)
    logger.info(
        f"rule toggled via admin UI | rule_id={body.rule_id} enabled={body.enabled}"
    )
    return {"rule_id": body.rule_id, "enabled": body.enabled}
