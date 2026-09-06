from unittest.mock import patch

from fastapi.testclient import TestClient

from compliance_service.api.main import app
from compliance_service.api.routes.admin import _effective_rules

client = TestClient(app)

_POLICIES = {
    "compliance": {"missing_client_id": {"enabled": True}},
    "surveillance": {"wash_trading": {"enabled": True}},
}


class TestEffectiveRules:
    @patch("compliance_service.api.routes.admin.load_policies", return_value=_POLICIES)
    @patch("compliance_service.api.routes.admin.RuleOverrideRepository")
    def test_falls_back_to_yaml_default_when_no_override(
        self, mock_repo_cls, _mock_policies
    ):
        mock_repo_cls.return_value.get_all.return_value = {}
        rules = {r["rule_id"]: r for r in _effective_rules()}
        assert rules["wash_trading"]["enabled"] is True
        assert rules["wash_trading"]["overridden"] is False

    @patch("compliance_service.api.routes.admin.load_policies", return_value=_POLICIES)
    @patch("compliance_service.api.routes.admin.RuleOverrideRepository")
    def test_override_takes_precedence_over_yaml_default(
        self, mock_repo_cls, _mock_policies
    ):
        mock_repo_cls.return_value.get_all.return_value = {"wash_trading": False}
        rules = {r["rule_id"]: r for r in _effective_rules()}
        assert rules["wash_trading"]["enabled"] is False
        assert rules["wash_trading"]["overridden"] is True
        # unrelated rules are untouched
        assert rules["missing_client_id"]["enabled"] is True
        assert rules["missing_client_id"]["overridden"] is False

    @patch("compliance_service.api.routes.admin.load_policies", return_value={})
    @patch("compliance_service.api.routes.admin.RuleOverrideRepository")
    def test_returns_all_ten_catalog_rules(self, mock_repo_cls, _mock_policies):
        mock_repo_cls.return_value.get_all.return_value = {}
        assert len(_effective_rules()) == 10


class TestAdminCompliancePage:
    @patch("compliance_service.api.routes.admin.load_policies", return_value=_POLICIES)
    @patch("compliance_service.api.routes.admin.RuleOverrideRepository")
    def test_renders_all_catalog_rules(self, mock_repo_cls, _mock_policies):
        mock_repo_cls.return_value.get_all.return_value = {}
        resp = client.get("/admin/compliance")
        assert resp.status_code == 200
        assert b"Wash Trading" in resp.content
        assert b"Missing Client ID" in resp.content


class TestToggleRuleEndpoint:
    @patch("compliance_service.api.routes.admin.RuleOverrideRepository")
    def test_toggle_valid_rule_upserts_and_returns_status(self, mock_repo_cls):
        resp = client.post(
            "/api/compliance/toggle", json={"rule_id": "wash_trading", "enabled": False}
        )
        assert resp.status_code == 200
        assert resp.json() == {"rule_id": "wash_trading", "enabled": False}
        mock_repo_cls.return_value.upsert.assert_called_once_with("wash_trading", False)

    @patch("compliance_service.api.routes.admin.RuleOverrideRepository")
    def test_toggle_unknown_rule_id_returns_404(self, mock_repo_cls):
        resp = client.post(
            "/api/compliance/toggle", json={"rule_id": "not_a_rule", "enabled": True}
        )
        assert resp.status_code == 404
        mock_repo_cls.return_value.upsert.assert_not_called()
