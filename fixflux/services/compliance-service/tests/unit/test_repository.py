"""Tests for ViolationRepository and AuditRepository using mocked SQLAlchemy sessions."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from compliance_service.repository.audit_repository import AuditRepository
from compliance_service.repository.violation_repository import ViolationRepository
from compliance_service.rules.base import Severity, Violation


def _make_violation(**kwargs) -> Violation:
    defaults = dict(
        rule_name="TradeSizeRule",
        rule_category="compliance",
        severity=Severity.HIGH,
        description="Quantity exceeds limit",
        raw_event={"symbol": "BTCUSD", "quantity": 500},
        client_id="CLIENT1",
        symbol="BTCUSD",
    )
    return Violation(**{**defaults, **kwargs})


def _mock_session():
    s = MagicMock()
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


class TestViolationRepositorySave:
    def test_save_adds_and_commits(self):
        mock_session = _mock_session()
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            repo = ViolationRepository()
            repo.save(_make_violation(), risk_contribution=20.0)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.rule_name == "TradeSizeRule"
        assert added.severity == "HIGH"
        assert added.risk_contribution == 20.0
        assert added.status == "OPEN"

    def test_save_closes_session_on_success(self):
        mock_session = _mock_session()
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            ViolationRepository().save(_make_violation(), risk_contribution=5.0)
        mock_session.close.assert_called_once()


class TestViolationRepositoryUpsertRiskScore:
    def test_creates_new_risk_score_record(self):
        mock_session = _mock_session()
        mock_session.get.return_value = None
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            ViolationRepository().upsert_risk_score("CLIENT1", 20.0, is_high_risk=False)

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.client_id == "CLIENT1"
        assert added.risk_score == 20.0
        assert added.violation_count == 1

    def test_updates_existing_risk_score_record(self):
        mock_session = _mock_session()
        existing = MagicMock()
        existing.risk_score = 80.0
        existing.violation_count = 4
        mock_session.get.return_value = existing
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            ViolationRepository().upsert_risk_score("CLIENT1", 20.0, is_high_risk=True)

        assert existing.risk_score == 100.0
        assert existing.violation_count == 5
        assert existing.is_high_risk is True
        mock_session.commit.assert_called_once()


class TestViolationRepositoryListAndGet:
    def _make_orm_violation(self, **kwargs):
        v = MagicMock()
        v.id = "00000000-0000-0000-0000-000000000001"
        v.rule_name = "TradeSizeRule"
        v.rule_category = "compliance"
        v.client_id = "CLIENT1"
        v.symbol = "BTCUSD"
        v.order_id = None
        v.severity = "HIGH"
        v.description = "Quantity exceeds limit"
        v.status = "OPEN"
        v.risk_contribution = 20.0
        v.detected_at = datetime.now(timezone.utc)
        v.reviewed_at = None
        v.reviewed_by = None
        for k, val in kwargs.items():
            setattr(v, k, val)
        return v

    def test_list_violations_returns_dicts(self):
        mock_session = _mock_session()
        orm_v = self._make_orm_violation()
        mock_session.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            orm_v
        ]
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            orm_v
        ]
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            results = ViolationRepository().list_violations(limit=10)
        assert isinstance(results, list)

    def test_get_by_id_found(self):
        mock_session = _mock_session()
        orm_v = self._make_orm_violation()
        mock_session.get.return_value = orm_v
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            result = ViolationRepository().get_by_id("some-id")
        assert result is not None
        assert result["rule_name"] == "TradeSizeRule"
        assert result["severity"] == "HIGH"

    def test_get_by_id_not_found(self):
        mock_session = _mock_session()
        mock_session.get.return_value = None
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            result = ViolationRepository().get_by_id("missing-id")
        assert result is None

    def test_update_status_returns_true_when_found(self):
        mock_session = _mock_session()
        orm_v = MagicMock()
        mock_session.get.return_value = orm_v
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            result = ViolationRepository().update_status(
                "id", "REVIEWED", "analyst@firm.com"
            )
        assert result is True
        assert orm_v.status == "REVIEWED"
        assert orm_v.reviewed_by == "analyst@firm.com"

    def test_update_status_returns_false_when_not_found(self):
        mock_session = _mock_session()
        mock_session.get.return_value = None
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            result = ViolationRepository().update_status("bad-id", "REVIEWED", None)
        assert result is False

    def test_list_risk_scores(self):
        mock_session = _mock_session()
        score = MagicMock()
        score.client_id = "CLIENT1"
        score.risk_score = 100.0
        score.violation_count = 5
        score.last_violation_at = datetime.now(timezone.utc)
        score.is_high_risk = False
        score.updated_at = datetime.now(timezone.utc)
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            score
        ]
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            results = ViolationRepository().list_risk_scores()
        assert len(results) == 1
        assert results[0]["client_id"] == "CLIENT1"

    def test_get_risk_score_not_found(self):
        mock_session = _mock_session()
        mock_session.get.return_value = None
        with patch(
            "compliance_service.repository.violation_repository.SessionLocal",
            return_value=mock_session,
        ):
            result = ViolationRepository().get_risk_score("UNKNOWN")
        assert result is None


class TestAuditRepository:
    def _make_audit_entry(self):
        e = MagicMock()
        e.id = 1
        e.event_type = "order_received"
        e.client_id = "CLIENT1"
        e.entity_id = None
        e.entity_type = None
        e.action = "raw_orders_consumed"
        e.payload = {"symbol": "EURUSD"}
        e.checksum = "abc123"
        e.recorded_at = datetime.now(timezone.utc)
        return e

    def test_list_entries_returns_dicts(self):
        mock_session = _mock_session()
        entry = self._make_audit_entry()
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            entry
        ]
        with patch(
            "compliance_service.repository.audit_repository.SessionLocal",
            return_value=mock_session,
        ):
            results = AuditRepository().list_entries()
        assert len(results) == 1
        assert results[0]["event_type"] == "order_received"
        assert results[0]["checksum"] == "abc123"

    def test_list_entries_empty(self):
        mock_session = _mock_session()
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )
        with patch(
            "compliance_service.repository.audit_repository.SessionLocal",
            return_value=mock_session,
        ):
            results = AuditRepository().list_entries()
        assert results == []
