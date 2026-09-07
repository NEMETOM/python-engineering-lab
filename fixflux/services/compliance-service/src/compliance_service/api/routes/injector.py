from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from compliance_service.fix_parser import (
    FixParseError,
    parse_new_order_single,
    to_raw_order_event,
)
from compliance_service.injector_producer import TARGET_TOPIC, InjectorProducer
from compliance_service.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["injector"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@lru_cache
def get_producer() -> InjectorProducer:
    # Lazy + cached: the real Kafka connection is only opened on first use,
    # and tests can override this dependency instead of hitting a broker.
    return InjectorProducer()


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"target_topic": TARGET_TOPIC, "active_tab": "injector"},
    )


@router.post("/api/orders/inject")
def inject_orders(
    raw_text: str = Form(default=""),
    file: UploadFile | None = None,
    producer: InjectorProducer = Depends(get_producer),
):
    if file is not None and file.filename:
        content = file.file.read().decode("utf-8", errors="replace")
    else:
        content = raw_text

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="No FIX message lines provided.")

    results: list[dict[str, object]] = []
    for line in lines:
        try:
            parsed = parse_new_order_single(line)
        except FixParseError as exc:
            logger.warning(f"rejected line {line!r}: {exc}")
            results.append({"raw_line": line, "status": "error", "error": str(exc)})
            continue

        event = to_raw_order_event(parsed)
        producer.send(event)
        logger.info(f"published order from line {line!r}: {event}")
        results.append(
            {"raw_line": line, "status": "published", "parsed": parsed, "event": event}
        )

    producer.flush()

    published = sum(1 for r in results if r["status"] == "published")
    return {
        "topic": TARGET_TOPIC,
        "total": len(results),
        "published": published,
        "errors": len(results) - published,
        "results": results,
    }
