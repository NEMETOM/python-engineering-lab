import asyncio
import threading

from pydantic import ValidationError

from market_data_api.connection_manager import ConnectionManager
from market_data_api.schemas import MarketDataEvent
from market_data_api.utils.logger import get_logger
from shared.infrastructure.kafka_client import create_consumer

logger = get_logger(__name__)

_TOPIC = "market_data"
_GROUP_ID = "market-data-api"


class MarketDataConsumer:
    """Consumes market_data (kafka-python, synchronous - same shared factory
    every other service uses) on a background thread, and rebroadcasts each
    validated event to WebSocket clients via the asyncio event loop.

    Kafka I/O and WebSocket broadcast run on different threads by design: the
    consumer thread can't call ConnectionManager's async methods directly, so
    each broadcast is handed to the event loop with run_coroutine_threadsafe -
    the standard bridge between a sync thread and a running asyncio loop.
    """

    def __init__(self, manager: ConnectionManager, loop: asyncio.AbstractEventLoop):
        self._manager = manager
        self._loop = loop
        self._consumer = create_consumer(_TOPIC, _GROUP_ID)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="market-data-api-consumer"
        )
        self._thread.start()
        logger.info(f"consumer thread started on topic={_TOPIC}")

    def stop(self) -> None:
        self._consumer.close()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("consumer thread stopped")

    def _run(self) -> None:
        for msg in self._consumer:
            try:
                event = MarketDataEvent(**msg.value)
            except ValidationError as exc:
                logger.warning(f"skipping malformed market_data message: {exc}")
                continue

            payload = event.model_dump(mode="json")
            asyncio.run_coroutine_threadsafe(
                self._manager.broadcast(payload), self._loop
            )
