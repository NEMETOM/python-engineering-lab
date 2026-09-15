import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from market_data_api.connection_manager import ConnectionManager
from market_data_api.consumer import MarketDataConsumer
from market_data_api.utils.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    consumer = MarketDataConsumer(manager, loop)
    consumer.start()
    try:
        yield
    finally:
        consumer.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Market Data WebSocket API", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "market-data-api"}

    @app.websocket("/ws/market-data")
    async def market_data_feed(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                # Clients don't send anything meaningful here - this just
                # blocks until the socket closes, so we notice a disconnect.
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(websocket)

    return app


app = create_app()
