import asyncio
import queue
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from behave import given, then, when
from fastapi.testclient import TestClient

from market_data_api.connection_manager import ConnectionManager

_RECEIVE_TIMEOUT_S = 5.0
_STOP = object()


class FakeKafkaConsumer:
    """Stands in for kafka.KafkaConsumer at the shared factory's patch point.

    Iterating blocks on a queue that the steps feed, so messages only arrive
    after clients have connected - like a live topic, unlike a fixed list that
    would be drained before the first WebSocket opened. close() unblocks the
    iterator so the consumer thread exits on app shutdown.
    """

    def __init__(self, *topics, **config):
        self.topics = topics
        self.config = config
        self._queue: queue.Queue = queue.Queue()

    def publish(self, value: dict) -> None:
        self._queue.put(SimpleNamespace(value=value))

    def __iter__(self):
        while (msg := self._queue.get()) is not _STOP:
            yield msg

    def close(self) -> None:
        self._queue.put(_STOP)


def _num(text: str) -> float | None:
    return None if text == "null" else float(text)


def _make_event(**overrides):
    defaults = {
        "symbol": "AAPL",
        "best_bid": 175.0,
        "best_ask": 175.5,
        "mid_price": 175.25,
        "last_trade_price": 175.0,
        "timestamp": "2026-10-25T12:00:00Z",
    }
    return {**defaults, **overrides}


def _receive_json(ws) -> dict:
    """WebSocketTestSession.receive_json() blocks forever if nothing arrives;
    bound it so a broken broadcast fails the scenario instead of hanging it."""
    # Not `with ThreadPoolExecutor(...)`: its exit waits for the worker, which
    # is the very thread stuck in receive_json() - the timeout would never
    # return. shutdown(wait=False) abandons it; the socket close in
    # after_scenario then unblocks it.
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(ws.receive_json)
    try:
        return future.result(timeout=_RECEIVE_TIMEOUT_S)
    except FutureTimeout as exc:
        raise AssertionError(
            f"no message within {_RECEIVE_TIMEOUT_S}s on the WebSocket"
        ) from exc
    finally:
        pool.shutdown(wait=False)


def _wait_for_connections(manager: ConnectionManager, expected: int) -> None:
    # connect() sends accept() before adding the socket to the manager, so a
    # client can be open before it is registered for broadcasts. Wait for the
    # registration, or a message published immediately could miss it.
    deadline = time.monotonic() + _RECEIVE_TIMEOUT_S
    while len(manager._connections) != expected:
        if time.monotonic() > deadline:
            raise AssertionError(
                f"expected {expected} registered connections, "
                f"got {len(manager._connections)}"
            )
        time.sleep(0.01)


# ── App-level steps ──────────────────────────────────────────────────────────


@given("the market data API is running")
def step_api_running(context):
    def _factory(*topics, **config):
        context.fake_kafka = FakeKafkaConsumer(*topics, **config)
        return context.fake_kafka

    context.stack.enter_context(
        patch("shared.infrastructure.kafka_client.KafkaConsumer", side_effect=_factory)
    )
    from market_data_api.api.main import app, manager

    context.manager = manager
    context.client = context.stack.enter_context(TestClient(app))
    context.clients = []


@given("{count:d} WebSocket clients are connected")
def step_clients_connected(context, count):
    for _ in range(count):
        ws = context.stack.enter_context(
            context.client.websocket_connect("/ws/market-data")
        )
        context.clients.append(ws)
    _wait_for_connections(context.manager, count)


@when('market data for "{symbol}" with bid {bid} and ask {ask} is published')
def step_publish(context, symbol, bid, ask):
    best_bid, best_ask = _num(bid), _num(ask)
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else None
    context.fake_kafka.publish(
        _make_event(symbol=symbol, best_bid=best_bid, best_ask=best_ask, mid_price=mid)
    )


@when('a market data message missing "{field}" is published')
def step_publish_malformed(context, field):
    event = _make_event()
    del event[field]
    context.fake_kafka.publish(event)


@when("{leaving:d} of the clients disconnect")
def step_disconnect(context, leaving):
    for ws in context.clients[:leaving]:
        ws.close()
    context.clients = context.clients[leaving:]


@then('every client receives a snapshot for "{symbol}" with mid price {mid}')
def step_every_client_receives(context, symbol, mid):
    context.received = [_receive_json(ws) for ws in context.clients]
    for payload in context.received:
        assert payload["symbol"] == symbol, payload
        if mid == "null":
            assert payload["mid_price"] is None, payload
        else:
            assert abs(payload["mid_price"] - float(mid)) < 1e-9, payload


@then("the snapshot has best bid {bid} and best ask {ask}")
def step_snapshot_sides(context, bid, ask):
    for payload in context.received:
        assert payload["best_bid"] == _num(bid), payload
        assert payload["best_ask"] == _num(ask), payload


@then('the first snapshot every client receives is for "{symbol}"')
def step_first_snapshot(context, symbol):
    for ws in context.clients:
        payload = _receive_json(ws)
        assert payload["symbol"] == symbol, payload


@then("the API tracks {count:d} connections")
def step_tracks(context, count):
    _wait_for_connections(context.manager, count)


@then('GET /health returns status "{status}" for service "{service}"')
def step_health(context, status, service):
    resp = context.client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": status, "service": service}


@then('the Kafka consumer subscribes to "{topic}" with {setting} set to "{value}"')
def step_consumer_config(context, topic, setting, value):
    assert context.fake_kafka.topics == (topic,)
    assert str(context.fake_kafka.config[setting]) == value


# ── ConnectionManager steps ──────────────────────────────────────────────────


def _make_websocket(dead: bool) -> MagicMock:
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock(
        side_effect=ConnectionError("client gone") if dead else None
    )
    return ws


@given("a connection manager with {total:d} connections of which {dead:d} fail on send")
def step_manager_with_dead(context, total, dead):
    context.cm = ConnectionManager()
    context.sockets = [_make_websocket(dead=i < dead) for i in range(total)]

    async def _connect_all():
        for ws in context.sockets:
            await context.cm.connect(ws)

    asyncio.run(_connect_all())


@when("a market data payload is broadcast")
def step_broadcast(context):
    context.payload = _make_event()
    asyncio.run(context.cm.broadcast(context.payload))


@then("{alive:d} connections receive the payload")
def step_alive_receive(context, alive):
    delivered = [
        ws
        for ws in context.sockets
        if ws.send_json.await_count == 1 and ws.send_json.side_effect is None
    ]
    assert len(delivered) == alive
    for ws in delivered:
        ws.send_json.assert_awaited_once_with(context.payload)


@then("the manager tracks {alive:d} connections")
def step_manager_tracks(context, alive):
    assert len(context.cm._connections) == alive
