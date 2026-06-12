from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics in the text exposition format."""

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
