import uuid

from app.db.models import PreDeploymentScan
from app.db.sync_database import SyncSessionLocal
from app.services.scan_service import execute_pre_deployment_scan
from app.workers.celery_app import celery_app


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
