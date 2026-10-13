"""FastAPI application factory."""

from fastapi import FastAPI

from lt import __version__
from lt.api.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="ClearView", version=__version__)
    app.include_router(health.router)
    return app


app = create_app()
