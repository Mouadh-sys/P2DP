import uuid

from opentelemetry import trace

from app.db.models import DeploymentRun, Environment, Project
from app.db.sync_database import SyncSessionLocal
from app.services.deploy_service import execute_deployment
from app.workers.celery_app import celery_app
from app.workers.scan_tasks import scan_post_deployment_task

tracer = trace.get_tracer("p2dp.deploy")


@celery_app.task(name="deploy_environment_task")
def deploy_environment_task(deployment_id: str) -> dict[str, str]:
    parsed_id = uuid.UUID(deployment_id)

    with tracer.start_as_current_span(
        "deploy_environment_task",
        attributes={"deployment_id": deployment_id},
    ):
        with SyncSessionLocal() as db:
            deployment_run = db.get(DeploymentRun, parsed_id)
            if not deployment_run:
                return {"status": "FAILED", "deployment_id": deployment_id, "detail": "Deployment not found"}

            environment = db.get(Environment, deployment_run.env_id)
            if not environment:
                deployment_run.status = "FAILED"
                deployment_run.finished_at = deployment_run.started_at
                db.commit()
                return {"status": "FAILED", "deployment_id": deployment_id, "detail": "Environment not found"}

            project = db.get(Project, environment.project_id)
            if not project:
                deployment_run.status = "FAILED"
                db.commit()
                return {"status": "FAILED", "deployment_id": deployment_id, "detail": "Project not found"}

            try:
                execute_deployment(db, deployment_run, project.id)
            except Exception:
                db.refresh(deployment_run)

            if deployment_run.status == "SUCCESS":
                scan_post_deployment_task.delay(str(environment.id))

            return {
                "status": deployment_run.status,
                "deployment_id": str(deployment_run.id),
                "git_commit": deployment_run.git_commit or "",
                "trace_id": deployment_run.trace_id or "",
            }
