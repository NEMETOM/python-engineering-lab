import time

from fastapi import FastAPI, Request
from prometheus_client import make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware

from compliance_service.api.routes.audit import router as audit_router
from compliance_service.api.routes.health import router as health_router
from compliance_service.api.routes.risk import router as risk_router
from compliance_service.api.routes.violations import router as violations_router
from compliance_service.infrastructure.db import Base, engine
from compliance_service.utils.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


class _MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - t0
        logger.debug(
            f"{request.method} {request.url.path} -> {response.status_code} "
            f"({elapsed * 1000:.1f}ms)"
        )
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="Compliance & Surveillance API",
        description=(
            "RegTech compliance engine for the FIX Protocol Simulator Pro. "
            "Detects rule violations, tracks risk scores, and maintains an immutable audit trail."
        ),
        version="1.0.0",
    )

    Base.metadata.create_all(bind=engine)
    logger.info("Compliance database tables ensured")

    app.include_router(health_router)
    app.include_router(violations_router)
    app.include_router(risk_router)
    app.include_router(audit_router)
    app.add_middleware(_MetricsMiddleware)
    app.mount("/metrics", make_asgi_app())

    return app


app = create_app()
