import json
import re

import pytest
from fastapi.testclient import TestClient

from compliance_service.api.main import app

client = TestClient(app)


def _ws_config(html: str) -> dict:
    match = re.search(
        r'<script id="ws-config" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match, "ws-config block missing"
    return json.loads(match.group(1))


class TestMarketDataPage:
    def test_page_renders(self):
        resp = client.get("/market-data")
        assert resp.status_code == 200
        assert "Live Market Data" in resp.text

    def test_defaults_to_deriving_the_url_from_the_browser_host(self, monkeypatch):
        # No fixed host baked in: the same page must work via the droplet IP
        # and via an SSH tunnel on localhost.
        monkeypatch.delenv("MARKET_DATA_WS_URL", raising=False)
        cfg = _ws_config(client.get("/market-data").text)
        assert cfg == {"url": None, "port": 8006, "path": "/ws/market-data"}

    def test_explicit_url_overrides_the_derived_one(self, monkeypatch):
        monkeypatch.setenv("MARKET_DATA_WS_URL", "wss://example.test/ws/market-data")
        cfg = _ws_config(client.get("/market-data").text)
        assert cfg["url"] == "wss://example.test/ws/market-data"

    def test_streamed_values_are_never_written_as_html(self):
        # Snapshot fields come from the network; innerHTML would be an XSS sink.
        html = client.get("/market-data").text
        script = html.split('<script id="ws-config"', 1)[1]
        assert "innerHTML" not in script
        assert "textContent" in script


class TestConsoleNavigation:
    @pytest.mark.parametrize(
        "path, active_label",
        [
            ("/market-data", "Market Data"),
            ("/", "Fix Msg Injector"),
        ],
    )
    def test_market_data_tab_is_in_the_shared_nav(self, path, active_label):
        html = client.get(path).text
        assert 'href="/market-data"' in html
        active = re.search(
            r'border-emerald-500 text-emerald-400"\s*>([^<]+)</a>', html
        ).group(1)
        assert active == active_label
