import time

from fastapi import FastAPI, Request
from prometheus_client import make_asgi_app
from shared.infrastructure.db import Base, engine
from shared.observability.metrics import api_request_latency, api_requests
from starlette.middleware.base import BaseHTTPMiddleware
from trade_store.api.routes import router


class _PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        t0 = time.perf_counter()
        response = await call_next(request)
        api_requests.labels(
            endpoint=request.url.path,
            method=request.method,
            status_code=str(response.status_code),
        ).inc()
        api_request_latency.labels(endpoint=request.url.path).observe(
            time.perf_counter() - t0
        )
        return response


def create_app():

    app = FastAPI(title="Trade Store API")

    Base.metadata.create_all(bind=engine)

    app.include_router(router)

    app.add_middleware(_PrometheusMiddleware)

    app.mount("/metrics", make_asgi_app())

    return app


app = create_app()
