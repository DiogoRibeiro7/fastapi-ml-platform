import json
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import IngestionError, IngestionTooLargeError
from app.schemas.jobs import BatchJobResponse
from app.schemas.prediction import BatchPredictionRequest, TransactionInput
from app.services.batch_job_service import BatchJobService


def parse_transaction_records(raw: bytes) -> list[dict[str, Any]]:
    """Parse a raw ingestion payload into transaction records.

    Accepts a JSON array, a single JSON object, or newline-delimited JSON
    (one object per line). Raises ValueError for anything else.
    """

    text = raw.decode("utf-8").strip()
    if not text:
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        records: list[dict[str, Any]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
        return records

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("Payload must be a JSON object, array, or newline-delimited JSON.")


class IngestionService:
    """Ingest transactions from a raw payload and submit them as a batch job."""

    def __init__(self, batch_job_service: BatchJobService, max_records: int) -> None:
        self._batch_job_service = batch_job_service
        self._max_records = max_records

    async def ingest(self, raw: bytes) -> BatchJobResponse:
        """Parse, validate, and submit a payload of transactions for scoring."""

        try:
            records = parse_transaction_records(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise IngestionError(f"Could not parse ingestion payload: {exc}") from exc

        if not records:
            raise IngestionError("No transactions found in payload.")
        if len(records) > self._max_records:
            raise IngestionTooLargeError(
                f"Payload has {len(records)} records; the maximum is {self._max_records}."
            )

        try:
            transactions = [TransactionInput.model_validate(record) for record in records]
        except ValidationError as exc:
            raise IngestionError(f"Invalid transaction in payload: {exc}") from exc

        return await self._batch_job_service.submit(
            BatchPredictionRequest(transactions=transactions)
        )
