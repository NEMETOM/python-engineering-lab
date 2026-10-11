import time

from fastapi import FastAPI, Request
from prometheus_client import make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware

from shared.infrastructure.db import Base, engine
from shared.observability.metrics import api_request_latency, api_requests
from trade_store.api.routes import router


class _PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        t0 = time.perf_counter()
        response = await call_next(request)
        # Use the matched route's path template (e.g. "/trades/{trade_id}"), not
        # request.url.path (e.g. "/trades/abc123") - the raw path creates one new
        # time series per unique trade_id ever queried, an unbounded-cardinality
        # label that grows forever. request.scope["route"] is only populated once
        # routing has resolved, which has already happened by this point since
        # we're past `await call_next(request)`. Falls back to the raw path for
        # unmatched routes (404s), where no route was ever resolved.
        route = request.scope.get("route")
        endpoint = route.path if route is not None else request.url.path
        api_requests.labels(
            endpoint=endpoint,
            method=request.method,
            status_code=str(response.status_code),
        ).inc()
        api_request_latency.labels(endpoint=endpoint).observe(time.perf_counter() - t0)
        return response


def create_app():

    app = FastAPI(title="Trade Store API")

    Base.metadata.create_all(bind=engine)

    app.include_router(router)

    app.add_middleware(_PrometheusMiddleware)

    app.mount("/metrics", make_asgi_app())

    return app


app = create_app()
