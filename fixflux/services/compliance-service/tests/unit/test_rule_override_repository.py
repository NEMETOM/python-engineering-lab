from unittest.mock import MagicMock, patch

from compliance_service.repository.rule_override_repository import (
    RuleOverrideRepository,
)


def _mock_session():
    s = MagicMock()
    s.__enter__ = MagicMock(return_value=s)
    s.__exit__ = MagicMock(return_value=False)
    return s


_PATCH_TARGET = "compliance_service.repository.rule_override_repository.SessionLocal"


class TestRuleOverrideRepositoryGetAll:
    def test_returns_rule_id_to_enabled_mapping(self):
        row1 = MagicMock(rule_id="wash_trading", enabled=False)
        row2 = MagicMock(rule_id="trade_size", enabled=True)
        mock_session = _mock_session()
        mock_session.query.return_value.all.return_value = [row1, row2]
        with patch(_PATCH_TARGET, return_value=mock_session):
            result = RuleOverrideRepository().get_all()
        assert result == {"wash_trading": False, "trade_size": True}

    def test_returns_empty_dict_when_no_overrides(self):
        mock_session = _mock_session()
        mock_session.query.return_value.all.return_value = []
        with patch(_PATCH_TARGET, return_value=mock_session):
            result = RuleOverrideRepository().get_all()
        assert result == {}

    def test_closes_session(self):
        mock_session = _mock_session()
        mock_session.query.return_value.all.return_value = []
        with patch(_PATCH_TARGET, return_value=mock_session):
            RuleOverrideRepository().get_all()
        mock_session.close.assert_called_once()


class TestRuleOverrideRepositoryUpsert:
    def test_inserts_new_row_when_none_exists(self):
        mock_session = _mock_session()
        mock_session.get.return_value = None
        with patch(_PATCH_TARGET, return_value=mock_session):
            RuleOverrideRepository().upsert("wash_trading", False)
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.rule_id == "wash_trading"
        assert added.enabled is False
        mock_session.commit.assert_called_once()

    def test_updates_existing_row_in_place(self):
        existing = MagicMock(rule_id="wash_trading", enabled=True)
        mock_session = _mock_session()
        mock_session.get.return_value = existing
        with patch(_PATCH_TARGET, return_value=mock_session):
            RuleOverrideRepository().upsert("wash_trading", False)
        mock_session.add.assert_not_called()
        assert existing.enabled is False
        mock_session.commit.assert_called_once()

    def test_closes_session(self):
        mock_session = _mock_session()
        mock_session.get.return_value = None
        with patch(_PATCH_TARGET, return_value=mock_session):
            RuleOverrideRepository().upsert("wash_trading", True)
        mock_session.close.assert_called_once()
