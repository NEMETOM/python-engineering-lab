from pydantic import BaseModel


class RuleToggleRequest(BaseModel):
    rule_id: str
    enabled: bool


class RuleStatus(BaseModel):
    rule_id: str
    category: str
    label: str
    enabled: bool
    overridden: bool
