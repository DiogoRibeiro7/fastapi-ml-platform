from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.config import Settings
from app.core.jobs import InlineJobQueue, JobQueue
from app.core.security import validate_api_key
from app.ml.model_provider import ModelProvider
from app.repositories.batch_job_repository import BatchJobRepository
from app.repositories.dead_letter_repository import DeadLetterRepository
from app.repositories.drift_report_repository import DriftReportRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.batch_job_service import BatchJobService
from app.services.calibration_service import CalibrationService
from app.services.drift_report_service import DriftReportService
from app.services.drift_service import DriftService
from app.services.evaluation_service import EvaluationService
from app.services.ingestion_service import IngestionService
from app.services.metrics_service import MetricsService
from app.services.model_registry_service import ModelRegistryService
from app.services.model_service import ModelService
from app.services.prediction_service import PredictionService
from app.services.threshold_service import ThresholdOptimizationService


def get_settings(request: Request) -> Settings:
    """Return request-scoped settings from the application state."""

    settings: Settings = request.app.state.settings
    return settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one async database session for the request."""

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Require a valid API key for protected endpoints."""

    settings = get_settings(request)
    try:
        validate_api_key(provided_key=x_api_key, expected_key=settings.api_key)
    except HTTPException:
        record_audit_event(
            "auth_failed",
            outcome="denied",
            reason="missing_api_key" if x_api_key is None else "invalid_api_key",
            method=request.method,
            path=request.url.path,
        )
        raise


def get_prediction_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PredictionRepository:
    """Build a prediction repository from the current database session."""

    return PredictionRepository(session=session)


def get_model_provider(request: Request) -> ModelProvider:
    """Return the application's live model provider."""

    provider: ModelProvider = request.app.state.model_provider
    return provider


def get_prediction_service(
    request: Request,
    repository: PredictionRepository = Depends(get_prediction_repository),
    provider: ModelProvider = Depends(get_model_provider),
) -> PredictionService:
    """Build the scoring service for a request."""

    settings: Settings = request.app.state.settings
    shap_explainer = provider.shap_explainer() if settings.enable_shap_explanations else None
    return PredictionService(
        repository=repository,
        model_bundle=provider.bundle,
        settings=settings,
        shap_explainer=shap_explainer,
    )


def get_model_service(
    provider: ModelProvider = Depends(get_model_provider),
) -> ModelService:
    """Build the model metadata service."""

    return ModelService(model_bundle=provider.bundle)


def get_model_registry_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ModelRegistryRepository:
    """Build a model registry repository from the current database session."""

    return ModelRegistryRepository(session=session)


def get_model_registry_service(
    repository: ModelRegistryRepository = Depends(get_model_registry_repository),
    provider: ModelProvider = Depends(get_model_provider),
) -> ModelRegistryService:
    """Build the model registry service."""

    return ModelRegistryService(repository=repository, model_provider=provider)


def get_batch_job_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BatchJobRepository:
    """Build a batch-job repository from the current database session."""

    return BatchJobRepository(session=session)


def get_dead_letter_repository(
    session: AsyncSession = Depends(get_db_session),
) -> DeadLetterRepository:
    """Build a dead-letter repository from the current database session."""

    return DeadLetterRepository(session=session)


def get_batch_job_service(
    request: Request,
    repository: BatchJobRepository = Depends(get_batch_job_repository),
    dead_letter_repository: DeadLetterRepository = Depends(get_dead_letter_repository),
    provider: ModelProvider = Depends(get_model_provider),
) -> BatchJobService:
    """Build the batch-job service, selecting the configured job queue."""

    settings: Settings = request.app.state.settings
    queue: JobQueue = (
        InlineJobQueue() if settings.process_jobs_inline else request.app.state.job_queue
    )
    return BatchJobService(
        repository=repository,
        dead_letter_repository=dead_letter_repository,
        session_factory=request.app.state.session_factory,
        model_bundle=provider.bundle,
        settings=settings,
        queue=queue,
    )


def get_ingestion_service(
    request: Request,
    batch_job_service: BatchJobService = Depends(get_batch_job_service),
) -> IngestionService:
    """Build the ingestion service for the active request."""

    settings: Settings = request.app.state.settings
    return IngestionService(
        batch_job_service=batch_job_service,
        max_records=settings.max_ingest_records,
    )


def get_metrics_service(
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> MetricsService:
    """Build the model metrics service."""

    return MetricsService(repository=repository)


def get_drift_service(
    repository: PredictionRepository = Depends(get_prediction_repository),
) -> DriftService:
    """Build the drift-report service."""

    return DriftService(repository=repository)


def get_drift_report_repository(
    session: AsyncSession = Depends(get_db_session),
) -> DriftReportRepository:
    """Build a drift-report repository from the current database session."""

    return DriftReportRepository(session=session)


def get_drift_report_service(
    request: Request,
    repository: DriftReportRepository = Depends(get_drift_report_repository),
) -> DriftReportService:
    """Build the stored-drift-report service, selecting the configured job queue."""

    settings: Settings = request.app.state.settings
    queue: JobQueue = (
        InlineJobQueue() if settings.process_jobs_inline else request.app.state.job_queue
    )
    return DriftReportService(
        repository=repository,
        session_factory=request.app.state.session_factory,
        queue=queue,
    )


def get_calibration_service(
    provider: ModelProvider = Depends(get_model_provider),
) -> CalibrationService:
    """Build the calibration-report service for the active model."""

    return CalibrationService(model_bundle=provider.bundle)


def get_threshold_service(
    provider: ModelProvider = Depends(get_model_provider),
) -> ThresholdOptimizationService:
    """Build the threshold-optimization service for the active model."""

    return ThresholdOptimizationService(model_bundle=provider.bundle)


def get_evaluation_service(
    request: Request,
    provider: ModelProvider = Depends(get_model_provider),
) -> EvaluationService:
    """Build the offline-evaluation service for the active model."""

    settings: Settings = request.app.state.settings
    return EvaluationService(
        model_bundle=provider.bundle,
        default_threshold=settings.min_decline_score,
    )
