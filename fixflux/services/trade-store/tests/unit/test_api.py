from unittest.mock import patch

from fastapi.testclient import TestClient

from shared.observability.metrics import api_request_latency, api_requests
from trade_store.api.main import app

client = TestClient(app)


def _label_values(metric, label):
    return {
        sample.labels[label]
        for family in metric.collect()
        for sample in family.samples
        if label in sample.labels
    }


class TestHealthEndpoint:
    def test_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_returns_200_status_code(self):
        response = client.get("/health")
        assert response.status_code == 200


_SAMPLE_TRADE = {
    "trade_id": "T1",
    "symbol": "EURUSD",
    "price": 1.09,
    "quantity": 100,
    "timestamp": "2026-01-01T10:00:00",
}

_TRADE_FIELDS = {"trade_id", "symbol", "price", "quantity", "timestamp"}


class TestGetTradesEndpoint:
    def test_returns_all_trades(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = [_SAMPLE_TRADE]
            response = client.get("/trades")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_returns_empty_list_when_no_trades(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades")
        assert response.status_code == 200
        assert response.json() == []

    def test_response_schema_contains_all_fields(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = [_SAMPLE_TRADE]
            response = client.get("/trades")
        assert set(response.json()[0].keys()) == _TRADE_FIELDS

    def test_response_content_type_is_json(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades")
        assert "application/json" in response.headers["content-type"]

    def test_passes_symbol_filter_to_repo(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades?symbol=MSFT")
        assert response.status_code == 200
        mock_repo.get_all.assert_called_once_with("MSFT")

    def test_unknown_symbol_returns_empty_list(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades?symbol=UNKNOWN")
        assert response.status_code == 200
        assert response.json() == []

    def test_no_symbol_passes_none_to_repo(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_all.return_value = []
            response = client.get("/trades")
        assert response.status_code == 200
        mock_repo.get_all.assert_called_once_with(None)


class TestGetTradeByIdEndpoint:
    def test_returns_trade_when_found(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = _SAMPLE_TRADE
            response = client.get("/trades/T1")
        assert response.status_code == 200
        assert response.json()["trade_id"] == "T1"

    def test_response_schema_contains_all_fields(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = _SAMPLE_TRADE
            response = client.get("/trades/T1")
        assert set(response.json().keys()) == _TRADE_FIELDS

    def test_returns_404_when_not_found(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = None
            response = client.get("/trades/NOTEXIST")
        assert response.status_code == 404
        assert response.json()["detail"] == "trade not found"

    def test_404_response_contains_detail_key(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = None
            response = client.get("/trades/NOTEXIST")
        assert "detail" in response.json()


class TestPrometheusMiddlewareLabeling:
    """endpoint label must be the route template, not the raw URL - a raw path
    like "/trades/T1" creates one new time series per unique trade_id ever
    queried, an unbounded-cardinality label. See _PrometheusMiddleware."""

    def test_parameterized_route_labels_with_template_not_raw_path(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = _SAMPLE_TRADE
            client.get("/trades/T1")
            client.get("/trades/SOME-OTHER-ID")

        endpoints = _label_values(api_requests, "endpoint")
        assert "/trades/{trade_id}" in endpoints
        assert "T1" not in " ".join(endpoints)
        assert "SOME-OTHER-ID" not in " ".join(endpoints)

    def test_unmatched_route_falls_back_to_raw_path(self):
        response = client.get("/this-route-does-not-exist")

        assert response.status_code == 404
        assert "/this-route-does-not-exist" in _label_values(api_requests, "endpoint")

    def test_latency_histogram_also_uses_route_template(self):
        with patch("trade_store.api.routes.repo") as mock_repo:
            mock_repo.get_by_id.return_value = _SAMPLE_TRADE
            client.get("/trades/ANOTHER-ID")

        assert "/trades/{trade_id}" in _label_values(api_request_latency, "endpoint")


class TestWrongMethods:
    def test_post_trades_returns_405(self):
        response = client.post("/trades")
        assert response.status_code == 405

    def test_delete_trades_returns_405(self):
        response = client.delete("/trades")
        assert response.status_code == 405

    def test_post_trade_by_id_returns_405(self):
        response = client.post("/trades/T1")
        assert response.status_code == 405

    def test_post_health_returns_405(self):
        response = client.post("/health")
        assert response.status_code == 405
