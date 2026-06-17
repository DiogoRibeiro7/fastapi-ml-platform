from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UserRepository:
    """Persistence operations for application users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, username: str, hashed_password: str, role: str) -> User:
        """Create and persist a user."""

        row = User(username=username, hashed_password=hashed_password, role=role)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a user by username."""

        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
