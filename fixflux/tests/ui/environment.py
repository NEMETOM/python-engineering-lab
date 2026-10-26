"""Hermetic UI tests for the FixFlux Console (Playwright + behave).

The real compliance-api FastAPI app runs in a background thread; only its
outside world is faked:
  - Kafka: the injector's producer is a recording fake (dependency override)
  - Postgres: rule overrides live in an in-memory fake repository, and table
    creation is disabled (the models use Postgres-only column types)
  - market-data-api: the browser's WebSocket is intercepted with
    page.route_web_socket, so steps push snapshots straight into the page
  - Tailwind CDN: answered with a stub that only defines .hidden, so the tests
    run offline and show/hide still behaves as in the real page

Run from fixflux/tests/ui:  behave
Headed, slowed down for demos:  UI_HEADED=1 UI_SLOW_MO=300 behave
"""

import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

_HERE = Path(__file__).resolve().parent
_FIXFLUX = _HERE.parent.parent
for _p in (_FIXFLUX, _FIXFLUX / "services" / "compliance-service" / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Never connected to: every DB touchpoint the three pages use is faked below.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://ui:ui@127.0.0.1:1/ui")
os.environ.pop("MARKET_DATA_WS_URL", None)

import compliance_service.infrastructure.db as _db

_db.Base.metadata.create_all = MagicMock()

import uvicorn
from compliance_service.api.main import app
from compliance_service.api.routes.injector import get_producer
from playwright.sync_api import sync_playwright

ARTIFACTS = _HERE / "artifacts"
HEADED = os.getenv("UI_HEADED") == "1"
SLOW_MO = int(os.getenv("UI_SLOW_MO", "0"))
TAILWIND_STUB = (
    "document.head.insertAdjacentHTML('beforeend',"
    "'<style>.hidden{display:none !important}</style>');"
)


class FakeProducer:
    """Records what the injector would have published to raw_orders."""

    def __init__(self):
        self.events: list[dict] = []

    def send(self, event: dict) -> None:
        self.events.append(event)

    def flush(self) -> None:
        pass


class FakeOverrideRepository:
    """In-memory stand-in for compliance_rule_overrides (shared by instances,
    like the real table)."""

    state: ClassVar[dict[str, bool]] = {}

    def get_all(self) -> dict[str, bool]:
        return dict(self.state)

    def upsert(self, rule_id: str, enabled: bool) -> None:
        self.state[rule_id] = enabled


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def before_all(context):
    context.producer = FakeProducer()
    app.dependency_overrides[get_producer] = lambda: context.producer
    # Steps reach the fake through context: importing environment.py from a
    # step module would load a second copy with its own, empty state.
    context.override_repo = FakeOverrideRepository
    context.repo_patch = patch(
        "compliance_service.api.routes.admin.RuleOverrideRepository",
        FakeOverrideRepository,
    )
    context.repo_patch.start()

    port = _free_port()
    context.server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    context.server_thread = threading.Thread(target=context.server.run, daemon=True)
    context.server_thread.start()
    deadline = time.monotonic() + 15
    while not context.server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("compliance-api did not start within 15s")
        time.sleep(0.05)
    context.base_url = f"http://127.0.0.1:{port}"

    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch(
        headless=not HEADED, slow_mo=SLOW_MO
    )


def before_scenario(context, scenario):
    context.producer.events.clear()
    FakeOverrideRepository.state.clear()

    context.browser_context = context.browser.new_context(base_url=context.base_url)
    context.browser_context.tracing.start(screenshots=True, snapshots=True)
    page = context.browser_context.new_page()
    page.route(
        "https://cdn.tailwindcss.com/**",
        lambda route: route.fulfill(
            content_type="application/javascript", body=TAILWIND_STUB
        ),
    )
    # Every market-data WebSocket the page opens lands here instead of
    # market-data-api; steps call .send() on the captured route.
    context.ws_routes = []
    # A real function, not ws_routes.append: Playwright rejects builtin methods
    # as route handlers.
    page.route_web_socket("**/ws/market-data", lambda ws: context.ws_routes.append(ws))
    context.page = page


def after_scenario(context, scenario):
    if scenario.status == "failed":
        ARTIFACTS.mkdir(exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in scenario.name)[:80]
        trace = ARTIFACTS / f"{safe}.zip"
        context.browser_context.tracing.stop(path=str(trace))
        print(f"  trace saved: {trace}  (open with: playwright show-trace {trace})")
    else:
        context.browser_context.tracing.stop()
    context.browser_context.close()


def after_all(context):
    context.browser.close()
    context.playwright.stop()
    context.server.should_exit = True
    context.server_thread.join(timeout=10)
    context.repo_patch.stop()
    app.dependency_overrides.clear()
