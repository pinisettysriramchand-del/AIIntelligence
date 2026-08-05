from arq.connections import RedisSettings

from stratiq.config import get_settings
from stratiq.infrastructure.queue.tasks import process_document


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 2
