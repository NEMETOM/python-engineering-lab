from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from compliance_service.api.main import create_app

_SAMPLE_VIOLATION = {
    "id": "00000000-0000-0000-0000-000000000001",
    "rule_name": "TradeSizeRule",
    "rule_category": "compliance",
    "client_id": "CLIENT1",
    "symbol": "BTCUSD",
    "order_id": None,
    "severity": "HIGH",
    "description": "Order quantity exceeds limit",
    "status": "OPEN",
    "risk_contribution": 20.0,
    "detected_at": "2026-01-01T10:00:00",
    "reviewed_at": None,
    "reviewed_by": None,
}

_SAMPLE_RISK = {
    "client_id": "CLIENT1",
    "risk_score": 20.0,
    "violation_count": 1,
    "last_violation_at": "2026-01-01T10:00:00",
    "is_high_risk": False,
    "updated_at": "2026-01-01T10:00:00",
}


@pytest.fixture
def client():
    with patch("compliance_service.infrastructure.db.Base.metadata") as mock_meta:
        mock_meta.create_all = MagicMock()
        app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


_VIOLATION_FIELDS = {
    "id", "rule_name", "rule_category", "client_id", "symbol", "order_id",
    "severity", "description", "status", "risk_contribution",
    "detected_at", "reviewed_at", "reviewed_by",
}


class TestViolationsEndpoints:
    def test_list_violations_returns_200(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_violations.return_value = [
                _SAMPLE_VIOLATION
            ]
            response = client.get("/violations")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_violations_empty_returns_empty_list(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_violations.return_value = []
            response = client.get("/violations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_violations_response_schema(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_violations.return_value = [
                _SAMPLE_VIOLATION
            ]
            response = client.get("/violations")
        assert set(response.json()[0].keys()) == _VIOLATION_FIELDS

    def test_get_violation_found(self, client):
        vid = "00000000-0000-0000-0000-000000000001"
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_id.return_value = _SAMPLE_VIOLATION
            response = client.get(f"/violations/{vid}")
        assert response.status_code == 200

    def test_get_violation_response_schema(self, client):
        vid = "00000000-0000-0000-0000-000000000001"
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_id.return_value = _SAMPLE_VIOLATION
            response = client.get(f"/violations/{vid}")
        assert set(response.json().keys()) == _VIOLATION_FIELDS

    def test_get_violation_not_found(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_by_id.return_value = None
            response = client.get("/violations/nonexistent-id")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_patch_violation_status(self, client):
        vid = "00000000-0000-0000-0000-000000000001"
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.update_status.return_value = True
            response = client.patch(
                f"/violations/{vid}/status",
                json={"status": "REVIEWED", "reviewed_by": "analyst@firm.com"},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "REVIEWED"

    def test_patch_invalid_status_returns_422(self, client):
        response = client.patch(
            "/violations/any-id/status",
            json={"status": "INVALID_STATUS"},
        )
        assert response.status_code == 422

    def test_patch_violation_not_found_returns_404(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.update_status.return_value = None
            response = client.patch(
                "/violations/nonexistent-id/status",
                json={"status": "REVIEWED", "reviewed_by": "analyst@firm.com"},
            )
        assert response.status_code == 404


class TestViolationsFilters:
    def test_filter_by_rule_name_passes_to_repo(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_violations.return_value = []
            response = client.get("/violations?rule_name=TradeSizeRule")
        assert response.status_code == 200
        mock_repo_cls.return_value.list_violations.assert_called_once_with(
            client_id=None, severity=None, status=None,
            rule_name="TradeSizeRule", limit=50,
        )

    def test_filter_by_severity_passes_to_repo(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_violations.return_value = []
            response = client.get("/violations?severity=HIGH")
        assert response.status_code == 200

    def test_invalid_severity_returns_422(self, client):
        response = client.get("/violations?severity=EXTREME")
        assert response.status_code == 422

    def test_invalid_status_returns_422(self, client):
        response = client.get("/violations?status=PENDING")
        assert response.status_code == 422

    def test_limit_zero_returns_422(self, client):
        response = client.get("/violations?limit=0")
        assert response.status_code == 422

    def test_limit_above_max_returns_422(self, client):
        response = client.get("/violations?limit=501")
        assert response.status_code == 422

    def test_limit_at_max_is_accepted(self, client):
        with patch(
            "compliance_service.api.routes.violations.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_violations.return_value = []
            response = client.get("/violations?limit=500")
        assert response.status_code == 200


class TestWrongMethods:
    def test_post_violations_returns_405(self, client):
        response = client.post("/violations")
        assert response.status_code == 405

    def test_delete_violation_by_id_returns_405(self, client):
        response = client.delete("/violations/some-id")
        assert response.status_code == 405

    def test_post_health_returns_405(self, client):
        response = client.post("/health")
        assert response.status_code == 405


class TestRiskEndpoints:
    def test_list_risk_scores(self, client):
        with patch(
            "compliance_service.api.routes.risk.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.list_risk_scores.return_value = [_SAMPLE_RISK]
            response = client.get("/risk")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_client_risk_found(self, client):
        with patch(
            "compliance_service.api.routes.risk.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_risk_score.return_value = _SAMPLE_RISK
            response = client.get("/risk/CLIENT1")
        assert response.status_code == 200
        assert response.json()["client_id"] == "CLIENT1"

    def test_get_client_risk_not_found(self, client):
        with patch(
            "compliance_service.api.routes.risk.ViolationRepository"
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_risk_score.return_value = None
            response = client.get("/risk/UNKNOWN")
        assert response.status_code == 404
