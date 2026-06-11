from typing import Any

from sqlalchemy import desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateModelError
from app.db.models import RegisteredModel


class ModelRegistryRepository:
    """Persistence operations for the model registry."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        version: str,
        artifact_path: str,
        training_dataset: str,
        metrics: dict[str, Any],
    ) -> RegisteredModel:
        """Register a new model version."""

        row = RegisteredModel(
            name=name,
            version=version,
            artifact_path=artifact_path,
            training_dataset=training_dataset,
            metrics=metrics,
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateModelError(
                f"Model {name} version {version} is already registered."
            ) from exc
        await self._session.refresh(row)
        return row

    async def list_all(self) -> list[RegisteredModel]:
        """Return all registered models, newest first."""

        result = await self._session.execute(
            select(RegisteredModel).order_by(
                desc(RegisteredModel.created_at), desc(RegisteredModel.id)
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, model_id: int) -> RegisteredModel | None:
        """Fetch a registered model by id."""

        result = await self._session.execute(
            select(RegisteredModel).where(RegisteredModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> RegisteredModel | None:
        """Return the currently active model, if any."""

        result = await self._session.execute(
            select(RegisteredModel).where(RegisteredModel.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def activate(self, model_id: int) -> RegisteredModel | None:
        """Activate one model and deactivate all others.

        Returns the activated model, or None when the id does not exist.
        """

        row = await self.get_by_id(model_id)
        if row is None:
            return None

        await self._session.execute(
            update(RegisteredModel)
            .where(RegisteredModel.id != model_id)
            .values(is_active=False)
        )
        row.is_active = True
        await self._session.commit()
        await self._session.refresh(row)
        return row
