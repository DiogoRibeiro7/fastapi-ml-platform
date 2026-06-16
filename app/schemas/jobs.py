from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

JobStatus = Literal["queued", "running", "completed", "failed"]


class BatchJobResponse(BaseModel):
    """Status and result of an asynchronous batch-scoring job."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    total: int
    completed: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: dict[str, Any] | None
    error: str | None


class DeadLetterResponse(BaseModel):
    """A transaction that failed scoring within a batch job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    transaction_id: str
    payload: dict[str, Any]
    error: str
    created_at: datetime


class DeadLetterListResponse(BaseModel):
    """Dead-lettered transactions for a job."""

    job_id: str
    dead_letters: list[DeadLetterResponse]
