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
