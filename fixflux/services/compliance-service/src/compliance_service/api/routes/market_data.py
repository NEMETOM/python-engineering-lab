import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["market-data"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# The browser connects to market-data-api directly, not through this service.
# Unset: the page derives ws(s)://<host the console was loaded from>:<port>/...,
# which works for both the droplet's IP and an SSH tunnel on localhost.
# Set MARKET_DATA_WS_URL to override, e.g. behind a reverse proxy.
MARKET_DATA_WS_PORT = int(os.getenv("MARKET_DATA_WS_PORT", "8006"))
MARKET_DATA_WS_PATH = "/ws/market-data"


@router.get("/market-data", response_class=HTMLResponse)
def market_data_page(request: Request):
    return templates.TemplateResponse(
        request,
        "market_data.html",
        {
            "active_tab": "market_data",
            "ws_url": os.getenv("MARKET_DATA_WS_URL") or None,
            "ws_port": MARKET_DATA_WS_PORT,
            "ws_path": MARKET_DATA_WS_PATH,
        },
    )
