from fastapi import FastAPI

from fix_injector.api.routes import router
from fix_injector.utils.logger import configure_logging

configure_logging()


def create_app():
    app = FastAPI(title="FIX Message Test Injector")
    app.include_router(router)
    return app


app = create_app()
