import asyncio

from fastapi import WebSocket

from market_data_api.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts JSON payloads to all
    of them. A dead connection found mid-broadcast is dropped, not raised -
    one slow/gone client must never block or fail the others."""

    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info(f"client connected, {len(self._connections)} active")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info(f"client disconnected, {len(self._connections)} active")

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            connections = list(self._connections)

        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"dropping dead connection: {exc}")
                await self.disconnect(websocket)
