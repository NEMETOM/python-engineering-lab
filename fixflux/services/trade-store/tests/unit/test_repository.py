from datetime import datetime
from unittest.mock import MagicMock, patch

from trade_store.repository import TradeRepository
from trade_store.schemas.trade_event import TradeEvent


def _make_event(**overrides):
    defaults = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
        timestamp=datetime.utcnow(),
    )
    return TradeEvent(**{**defaults, **overrides})


class TestRepositorySave:
    def test_save_calls_session_add(self):
        mock_session = MagicMock()
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            TradeRepository().save(_make_event())
        mock_session.add.assert_called_once()

    def test_save_calls_session_commit(self):
        mock_session = MagicMock()
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            TradeRepository().save(_make_event())
        mock_session.commit.assert_called_once()

    def test_save_calls_session_close_on_success(self):
        mock_session = MagicMock()
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            TradeRepository().save(_make_event())
        mock_session.close.assert_called_once()

    def test_save_calls_session_close_even_if_commit_raises(self):
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("DB error")
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            try:
                TradeRepository().save(_make_event())
            except Exception:
                pass
        mock_session.close.assert_called_once()

    def test_save_maps_all_fields_to_model(self):
        mock_session = MagicMock()
        ts = datetime(2024, 1, 15, 10, 30, 0)
        event = _make_event(
            trade_id="T999",
            symbol="MSFT",
            buy_order_id="B999",
            sell_order_id="S999",
            price=200.5,
            quantity=5,
            timestamp=ts,
        )
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            TradeRepository().save(event)
        added = mock_session.add.call_args[0][0]
        assert added.trade_id == "T999"
        assert added.symbol == "MSFT"
        assert added.buy_order_id == "B999"
        assert added.sell_order_id == "S999"
        assert added.price == 200.5
        assert added.quantity == 5
        assert added.timestamp == ts

    def test_save_propagates_commit_exception(self):
        mock_session = MagicMock()
        mock_session.commit.side_effect = RuntimeError("commit failed")
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            repo = TradeRepository()
            try:
                repo.save(_make_event())
                raised = False
            except RuntimeError:
                raised = True
        assert raised


def _make_mock_trade(**overrides):
    trade = MagicMock()
    trade.trade_id = overrides.get("trade_id", "T001")
    trade.symbol = overrides.get("symbol", "AAPL")
    trade.price = overrides.get("price", 150.0)
    trade.quantity = overrides.get("quantity", 10)
    # trade.timestamp is left as a MagicMock so .isoformat() is also a mock
    return trade


class TestRepositoryGetAll:
    def test_returns_all_trades_without_symbol_filter(self):
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [_make_mock_trade()]
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            result = TradeRepository().get_all()
        assert len(result) == 1
        assert result[0]["trade_id"] == "T001"

    def test_filters_by_symbol_when_provided(self):
        mock_session = MagicMock()
        mock_trade = _make_mock_trade(symbol="MSFT")
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_trade
        ]
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            result = TradeRepository().get_all(symbol="MSFT")
        assert result[0]["symbol"] == "MSFT"
        mock_session.query.return_value.filter.assert_called_once()

    def test_returns_empty_list_when_no_trades(self):
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            result = TradeRepository().get_all()
        assert result == []

    def test_closes_session(self):
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            TradeRepository().get_all()
        mock_session.close.assert_called_once()


class TestRepositoryGetById:
    def test_returns_trade_dict_when_found(self):
        mock_session = MagicMock()
        mock_session.query.return_value.get.return_value = _make_mock_trade(
            trade_id="T999"
        )
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            result = TradeRepository().get_by_id("T999")
        assert result is not None
        assert result["trade_id"] == "T999"

    def test_returns_none_when_not_found(self):
        mock_session = MagicMock()
        mock_session.query.return_value.get.return_value = None
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            result = TradeRepository().get_by_id("NOTEXIST")
        assert result is None

    def test_closes_session(self):
        mock_session = MagicMock()
        mock_session.query.return_value.get.return_value = None
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            TradeRepository().get_by_id("T001")
        mock_session.close.assert_called_once()

    def test_to_dict_maps_all_fields(self):
        mock_session = MagicMock()
        mock_trade = _make_mock_trade(
            trade_id="T888", symbol="TSLA", price=250.5, quantity=3
        )
        mock_trade.timestamp.isoformat.return_value = "2024-06-01T12:00:00"
        mock_session.query.return_value.get.return_value = mock_trade
        with patch("trade_store.repository.SessionLocal", return_value=mock_session):
            result = TradeRepository().get_by_id("T888")
        assert result["trade_id"] == "T888"
        assert result["symbol"] == "TSLA"
        assert result["price"] == 250.5
        assert result["quantity"] == 3
        assert result["timestamp"] == "2024-06-01T12:00:00"
