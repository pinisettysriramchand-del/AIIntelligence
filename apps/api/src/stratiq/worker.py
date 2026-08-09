"""ARQ worker settings and entry point."""

from __future__ import annotations

import logging

from stratiq.config import get_settings
from stratiq.infrastructure.queue.tasks import process_document_job, shutdown, startup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

_settings = get_settings()


class WorkerSettings:
    """ARQ worker configuration.

    Run with: arq stratiq.worker.WorkerSettings
    """

    functions = [process_document_job]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 5
    job_timeout = 600
    keep_result = 3600
    max_tries = _settings.processing_max_tries
    retry_jobs = True
