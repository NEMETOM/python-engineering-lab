from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Patched for the whole fixture lifetime, not just during import: the
    # lifespan (which constructs a real MarketDataConsumer -> real Kafka
    # connection attempt) only actually runs once `with test_client:` enters,
    # which must happen while this patch is still active.
    with patch("market_data_api.api.main.MarketDataConsumer") as mock_consumer_cls:
        mock_consumer_cls.return_value = MagicMock()
        from market_data_api.api.main import app, manager

        test_client = TestClient(app)
        with test_client:
            yield test_client, manager


class TestHealth:
    def test_health_returns_ok(self, client):
        test_client, _ = client
        resp = test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "service": "market-data-api"}


class TestWebSocketConnection:
    def test_connecting_registers_with_the_connection_manager(self, client):
        test_client, manager = client
        with test_client.websocket_connect("/ws/market-data"):
            assert len(manager._connections) == 1

    def test_disconnecting_removes_it_from_the_connection_manager(self, client):
        test_client, manager = client
        with test_client.websocket_connect("/ws/market-data"):
            pass
        assert len(manager._connections) == 0

    def test_two_clients_are_both_tracked(self, client):
        test_client, manager = client
        with (
            test_client.websocket_connect("/ws/market-data"),
            test_client.websocket_connect("/ws/market-data"),
        ):
            assert len(manager._connections) == 2
