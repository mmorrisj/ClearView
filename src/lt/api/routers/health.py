"""Liveness endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from lt import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health")
def health() -> HealthResponse:
    """Liveness only; does not touch the database."""
    return HealthResponse(status="ok", version=__version__)
