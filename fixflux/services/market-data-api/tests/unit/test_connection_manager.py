import asyncio
from unittest.mock import AsyncMock

from market_data_api.connection_manager import ConnectionManager


def _make_ws():
    ws = AsyncMock()
    return ws


class TestConnect:
    def test_accepts_and_tracks_connection(self):
        manager = ConnectionManager()
        ws = _make_ws()

        asyncio.run(manager.connect(ws))

        ws.accept.assert_called_once()
        assert ws in manager._connections


class TestDisconnect:
    def test_removes_connection(self):
        manager = ConnectionManager()
        ws = _make_ws()
        asyncio.run(manager.connect(ws))

        asyncio.run(manager.disconnect(ws))

        assert ws not in manager._connections

    def test_disconnecting_unknown_connection_is_a_noop(self):
        manager = ConnectionManager()
        ws = _make_ws()

        asyncio.run(manager.disconnect(ws))  # never connected - must not raise

        assert ws not in manager._connections


class TestBroadcast:
    def test_sends_payload_to_every_connection(self):
        manager = ConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        asyncio.run(manager.connect(ws1))
        asyncio.run(manager.connect(ws2))

        payload = {"symbol": "AAPL", "best_bid": 175.0}
        asyncio.run(manager.broadcast(payload))

        ws1.send_json.assert_called_once_with(payload)
        ws2.send_json.assert_called_once_with(payload)

    def test_dead_connection_is_dropped_not_raised(self):
        manager = ConnectionManager()
        dead, alive = _make_ws(), _make_ws()
        dead.send_json.side_effect = RuntimeError("connection closed")
        asyncio.run(manager.connect(dead))
        asyncio.run(manager.connect(alive))

        asyncio.run(manager.broadcast({"symbol": "AAPL"}))  # must not raise

        assert dead not in manager._connections
        assert alive in manager._connections
        alive.send_json.assert_called_once()

    def test_broadcast_with_no_connections_is_a_noop(self):
        manager = ConnectionManager()

        asyncio.run(manager.broadcast({"symbol": "AAPL"}))  # must not raise
