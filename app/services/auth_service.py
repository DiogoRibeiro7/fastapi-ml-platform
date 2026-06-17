from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.exceptions import DuplicateUserError, InvalidCredentialsError
from app.core.passwords import hash_password, verify_password
from app.core.principal import Role
from app.core.tokens import create_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserCreateRequest, UserResponse


class AuthService:
    """Authentication and user management."""

    def __init__(self, repository: UserRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def login(self, request: LoginRequest) -> TokenResponse:
        """Validate credentials and issue an access token."""

        user = await self._repository.get_by_username(request.username)
        if user is None or not verify_password(request.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid username or password.")

        expires = self._settings.access_token_expire_minutes
        token = create_access_token(
            subject=user.username,
            role=user.role,  # type: ignore[arg-type]
            secret=self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
            issued_at=datetime.now(UTC),
            expires_minutes=expires,
        )
        return TokenResponse(
            access_token=token,
            role=user.role,  # type: ignore[arg-type]
            expires_in=expires * 60,
        )

    async def create_user(self, request: UserCreateRequest) -> UserResponse:
        """Create a new user with a hashed password."""

        try:
            user = await self._repository.create(
                username=request.username,
                hashed_password=hash_password(request.password),
                role=request.role,
            )
        except IntegrityError as exc:
            raise DuplicateUserError(
                f"User already exists: {request.username}"
            ) from exc
        return UserResponse.model_validate(user)

    async def ensure_user(self, username: str, password: str, role: Role) -> None:
        """Create a user if it does not already exist (used for bootstrapping)."""

        if await self._repository.get_by_username(username) is not None:
            return
        await self._repository.create(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
