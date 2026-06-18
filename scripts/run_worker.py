"""Run an RQ worker that processes batch-scoring jobs from Redis.

Start one or more of these alongside the API when JOB_BACKEND=redis:

    python scripts/run_worker.py
"""

from __future__ import annotations

from redis import Redis
from rq import Queue, Worker

from app.core.config import Settings


def main() -> None:
    """Start an RQ worker bound to the configured Redis queue."""

    settings = Settings()
    connection = Redis.from_url(settings.redis_url)
    queue = Queue(connection=connection)
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()
