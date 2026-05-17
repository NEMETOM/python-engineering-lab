from unittest.mock import patch

from fastapi.testclient import TestClient
from trade_store.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_returns_200_status_code(self):
        response = client.get("/health")
        assert response.status_code == 200


class TestGetTradesEndpoint:
    def test_returns_all_trades(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = [{"trade_id": "T1", "symbol": "AAPL"}]
            response = client.get("/trades")
        assert response.status_code == 200
        assert response.json() == [{"trade_id": "T1", "symbol": "AAPL"}]

    def test_passes_symbol_filter_to_repo(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades?symbol=MSFT")
        assert response.status_code == 200
        mock_repo.get_all.assert_called_once_with("MSFT")

    def test_no_symbol_passes_none_to_repo(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades")
        assert response.status_code == 200
        mock_repo.get_all.assert_called_once_with(None)


class TestGetTradeByIdEndpoint:
    def test_returns_trade_when_found(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = {"trade_id": "T1", "symbol": "AAPL"}
            response = client.get("/trades/T1")
        assert response.status_code == 200
        assert response.json()["trade_id"] == "T1"

    def test_returns_404_when_not_found(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = None
            response = client.get("/trades/NOTEXIST")
        assert response.status_code == 404
        assert response.json()["detail"] == "trade not found"
