from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from fix_injector.api.main import app
from fix_injector.api.routes import get_producer


@pytest.fixture
def client():
    fake_producer = MagicMock()
    app.dependency_overrides[get_producer] = lambda: fake_producer
    try:
        yield TestClient(app), fake_producer
    finally:
        app.dependency_overrides.clear()


def test_index_page_renders(client):
    test_client, _ = client

    resp = test_client.get("/")

    assert resp.status_code == 200
    assert b"FIX Message Test Injector" in resp.content


def test_inject_valid_order_publishes_to_raw_orders(client):
    test_client, fake_producer = client

    resp = test_client.post(
        "/api/orders/inject",
        data={
            "raw_text": "8=FIX.4.2|35=D|49=CLIENT1|55=EURUSD|54=1|44=1.09000|38=100|"
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "topic": "raw_orders",
        "total": 1,
        "published": 1,
        "errors": 0,
        "results": body["results"],
    }
    assert body["results"][0]["status"] == "published"
    fake_producer.send.assert_called_once()
    fake_producer.flush.assert_called_once()


def test_inject_mixes_valid_and_invalid_lines(client):
    test_client, fake_producer = client

    resp = test_client.post(
        "/api/orders/inject",
        data={
            "raw_text": (
                "8=FIX.4.2|35=D|49=CLIENT1|55=EURUSD|54=1|44=1.09000|38=100|\n"
                "NOT_A_FIX_MESSAGE"
            )
        },
    )

    body = resp.json()
    assert body["total"] == 2
    assert body["published"] == 1
    assert body["errors"] == 1
    statuses = {r["status"] for r in body["results"]}
    assert statuses == {"published", "error"}
    fake_producer.send.assert_called_once()


def test_inject_rejects_empty_payload(client):
    test_client, fake_producer = client

    resp = test_client.post("/api/orders/inject", data={"raw_text": "   "})

    assert resp.status_code == 400
    fake_producer.send.assert_not_called()
