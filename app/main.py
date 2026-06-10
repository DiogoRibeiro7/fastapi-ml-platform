from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.session import build_session_factory, create_database_tables, dispose_engine
from app.ml.model_loader import load_model_bundle


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
        app.state.model_bundle = load_model_bundle(
            artifact_path=app_settings.model_artifact_path,
            metadata_path=app_settings.model_metadata_path,
        )

        await create_database_tables(engine)
        yield
        await dispose_engine(engine)

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description="Production-style FastAPI service for fraud-risk ML inference.",
        lifespan=lifespan,
    )

    app.include_router(api_router)
    return app


app = create_app()
