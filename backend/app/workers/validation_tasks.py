import uuid

from sqlalchemy import select

from app.db.models import Artifact, Environment, Project, TemplateVersion
from app.db.sync_database import SyncSessionLocal
from app.services.validation_service import run_validation
from app.workers.celery_app import celery_app

ARTIFACT_TYPE_VALIDATION_REPORT = "validation_report"


@celery_app.task(name="validate_template_task")
def validate_template_task(template_version_id: str) -> dict[str, str]:
    parsed_id = uuid.UUID(template_version_id)

    with SyncSessionLocal() as db:
        row = db.execute(
            select(TemplateVersion, Environment, Project)
            .join(Environment, TemplateVersion.env_id == Environment.id)
            .join(Project, Environment.project_id == Project.id)
            .where(TemplateVersion.id == parsed_id)
        ).first()
        if not row:
            return {"status": "error", "detail": "Template version not found"}

        template_version, environment, project = row
        outcome = run_validation(
            files_ref=template_version.files_ref,
            project_id=project.id,
            environment_id=environment.id,
            template_version_id=template_version.id,
        )

        artifact = Artifact(
            template_version_id=template_version.id,
            type=ARTIFACT_TYPE_VALIDATION_REPORT,
            storage_ref=outcome.storage_ref,
            status="passed" if outcome.success else "failed",
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        return {
            "status": "completed",
            "artifact_id": str(artifact.id),
            "validation_status": artifact.status,
            "storage_ref": artifact.storage_ref,
        }
