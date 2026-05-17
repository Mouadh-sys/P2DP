from app.workers.celery_app import celery_app


@celery_app.task
def run_task(payload: dict | None = None) -> dict[str, str]:
    return {"status": "queued"}
