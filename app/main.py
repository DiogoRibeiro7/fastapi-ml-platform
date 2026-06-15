import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.v1.router import api_router
from app.core.config import Settings
from app.core.correlation import correlation_id_middleware
from app.core.jobs import BackgroundJobQueue
from app.core.logging import configure_logging
from app.core.metrics import prometheus_middleware
from app.core.tracing import configure_tracing
from app.db.session import build_session_factory, create_database_tables, dispose_engine
from app.ml.model_loader import load_model_bundle, load_registered_bundle
from app.ml.model_provider import ModelProvider
from app.repositories.model_registry_repository import ModelRegistryRepository

logger = logging.getLogger(__name__)


async def _promote_active_registered_model(
    session_factory: async_sessionmaker[AsyncSession],
    model_provider: ModelProvider,
) -> None:
    """Serve the active registered model on startup, if one exists.

    This makes promotions survive restarts: whichever registry row is active
    is loaded over the default artifact. A missing or invalid artifact is
    logged and ignored so the service still starts on the default model.
    """

    async with session_factory() as session:
        active = await ModelRegistryRepository(session).get_active()

    if active is None:
        return

    try:
        bundle = load_registered_bundle(
            artifact_path=Path(active.artifact_path),
            name=active.name,
            version=active.version,
            metrics=active.metrics,
        )
    except (FileNotFoundError, TypeError):
        logger.exception(
            "Active registered model %s could not be loaded; serving the default model.",
            active.version,
        )
        return

    model_provider.swap(bundle)
    logger.info("Promoted registered model %s on startup.", active.version)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    The app factory keeps tests clean because each test can create an isolated
    application with its own settings and temporary database.
    """

    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(level=app_settings.log_level)

        engine, session_factory = build_session_factory(app_settings.database_url)
        app.state.settings = app_settings
        app.state.engine = engine
        app.state.session_factory = session_factory

        model_provider = ModelProvider(
            load_model_bundle(
                artifact_path=app_settings.model_artifact_path,
                metadata_path=app_settings.model_metadata_path,
                train_if_missing=app_settings.train_baseline_if_missing,
            )
        )
        app.state.model_provider = model_provider
        app.state.job_queue = BackgroundJobQueue()

        await create_database_tables(engine)
        await _promote_active_registered_model(session_factory, model_provider)
        yield
        await dispose_engine(engine)

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description="Production-style FastAPI service for fraud-risk ML inference.",
        lifespan=lifespan,
    )

    if app_settings.enable_tracing:
        configure_tracing(app, app_settings)

    app.middleware("http")(prometheus_middleware)
    # Added last so it is the outermost middleware: the correlation id is set
    # before request handling and other middleware run.
    app.middleware("http")(correlation_id_middleware)
    app.include_router(api_router)
    return app


app = create_app()
