from fastapi import FastAPI
from shared.infrastructure.db import Base, engine
from trade_store.api.routes import router


def create_app():

    app = FastAPI(title="Trade Store API")

    Base.metadata.create_all(bind=engine)

    app.include_router(router)

    return app


app = create_app()
