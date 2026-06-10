from typing import Any

from fastapi import APIRouter, Request, status
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Return a lightweight process-health response."""

    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness(request: Request) -> dict[str, Any]:
    """Check whether the app can serve traffic."""

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))

    model_bundle = request.app.state.model_bundle
    return {
        "status": "ready",
        "database": "ok",
        "model_version": model_bundle.version,
    }
