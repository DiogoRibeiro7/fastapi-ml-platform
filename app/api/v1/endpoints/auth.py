from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, require_roles
from app.core.exceptions import DuplicateUserError, InvalidCredentialsError
from app.core.principal import ADMIN_ROLES
from app.schemas.auth import LoginRequest, TokenResponse, UserCreateRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate with username and password and receive an access token."""

    try:
        return await service.login(request)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from exc


@router.post(
    "/auth/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
async def create_user(
    request: UserCreateRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Create a new user. Restricted to administrators."""

    try:
        return await service.create_user(request)
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
