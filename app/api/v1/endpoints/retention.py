from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import get_retention_service, require_roles
from app.core.principal import ADMIN_ROLES
from app.schemas.retention import RetentionCleanupResponse
from app.services.retention_service import RetentionService

router = APIRouter()


@router.post(
    "/admin/retention/cleanup",
    response_model=RetentionCleanupResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
async def cleanup_retention(
    request: Request,
    days: int | None = Query(default=None, ge=1),
    service: RetentionService = Depends(get_retention_service),
) -> RetentionCleanupResponse:
    """Delete records older than the retention window. Restricted to admins.

    The window defaults to the configured `data_retention_days`; the `days`
    query parameter overrides it for a one-off cleanup.
    """

    retention_days = days if days is not None else request.app.state.settings.data_retention_days
    if retention_days is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data retention is not configured; pass a 'days' parameter.",
        )

    deleted = await service.purge(retention_days)
    return RetentionCleanupResponse(retention_days=retention_days, deleted=deleted)
