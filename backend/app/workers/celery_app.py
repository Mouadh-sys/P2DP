from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "p2dp",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.validation_tasks",
        "app.workers.scan_tasks",
        "app.workers.deploy_tasks",
        "app.workers.risk_tasks",
    ],
)

from app.core.otel import setup_telemetry  # noqa: E402

setup_telemetry("p2dp-worker")
