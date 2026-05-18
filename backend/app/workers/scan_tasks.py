import uuid

from opentelemetry import trace

from app.db.models import PreDeploymentScan
from app.db.sync_database import SyncSessionLocal
from app.services.post_deployment_scan_service import PostDeploymentScanError, execute_post_deployment_scan
from app.services.scan_service import execute_pre_deployment_scan
from app.workers.celery_app import celery_app

tracer = trace.get_tracer("p2dp.scan")


@celery_app.task(name="scan_pre_deployment_task")
def scan_pre_deployment_task(scan_id: str) -> dict[str, str]:
    parsed_id = uuid.UUID(scan_id)

    with SyncSessionLocal() as db:
        scan = db.get(PreDeploymentScan, parsed_id)
        if not scan:
            return {"status": "FAILED", "detail": "Scan not found"}

        try:
            execute_pre_deployment_scan(db, scan)
        except Exception:
            db.refresh(scan)

        return {
            "status": scan.status,
            "scan_id": str(scan.id),
            "error_message": scan.error_message or "",
        }


@celery_app.task(name="scan_post_deployment_task")
def scan_post_deployment_task(env_id: str) -> dict[str, str | int]:
    parsed_env_id = uuid.UUID(env_id)

    with tracer.start_as_current_span(
        "scan_post_deployment_task",
        attributes={"env_id": env_id},
    ):
        with SyncSessionLocal() as db:
            try:
                result = execute_post_deployment_scan(db, parsed_env_id)
                return {
                    "status": result["status"],
                    "env_id": env_id,
                    "findings_count": result["findings_count"],
                    "source": result["source"],
                    "errors": result.get("errors", ""),
                }
            except (PostDeploymentScanError, ValueError) as exc:
                return {"status": "FAILED", "env_id": env_id, "detail": str(exc)}
