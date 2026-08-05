"""ARQ worker settings and entry point."""

from __future__ import annotations

import logging

from stratiq.infrastructure.queue.tasks import process_document, shutdown, startup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class WorkerSettings:
    """ARQ worker configuration.

    Run with: arq stratiq.worker.WorkerSettings
    """

    functions = [process_document]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 5
    job_timeout = 600
    keep_result = 3600
