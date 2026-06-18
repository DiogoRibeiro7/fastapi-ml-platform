from pydantic import BaseModel


class RetentionCleanupResponse(BaseModel):
    """Result of a data-retention cleanup run."""

    retention_days: int
    deleted: dict[str, int]
