import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DeploymentRun, Environment, TemplateVersion
from app.services.argo_service import ArgoSyncError, sync_application
from app.services.gitops_service import GitOpsError, commit_and_push, copy_manifests_to_gitops
from app.services.storage_service import storage_service


def _deployment_log_key(project_id: uuid.UUID, environment_id: uuid.UUID, deployment_id: uuid.UUID) -> str:
    return f"projects/{project_id}/envs/{environment_id}/deployments/{deployment_id}/deploy.log"


def execute_deployment(
    db: Session,
    deployment_run: DeploymentRun,
    project_id: uuid.UUID,
) -> None:
    environment = db.get(Environment, deployment_run.env_id)
    if not environment:
        raise ValueError("Environment not found")

    template_version = db.execute(
        select(TemplateVersion)
        .where(TemplateVersion.env_id == environment.id)
        .order_by(TemplateVersion.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not template_version:
        raise ValueError("No template version uploaded for this environment")

    log_lines: list[str] = [
        f"deployment_id={deployment_run.id}",
        f"environment_target={environment.target}",
        f"template_version_id={template_version.id}",
    ]

    try:
        manifest_dir = copy_manifests_to_gitops(
            files_ref=template_version.files_ref,
            env_target=environment.target,
            deployment_id=deployment_run.id,
        )
        log_lines.append(f"manifests_copied_to={manifest_dir}")

        commit_hash = commit_and_push(deployment_run.id, environment.target)
        deployment_run.git_commit = commit_hash
        log_lines.append(f"git_commit={commit_hash}")

        try:
            argo_message = sync_application(str(deployment_run.id))
            log_lines.append(argo_message)
        except ArgoSyncError as exc:
            log_lines.append(f"argocd_sync_warning={exc}")

        deployment_run.status = "SUCCESS"
    except Exception as exc:  # noqa: BLE001
        deployment_run.status = "FAILED"
        log_lines.append(f"error={exc}")
        raise
    finally:
        logs_ref = storage_service.upload_text(
            _deployment_log_key(project_id, environment.id, deployment_run.id),
            "\n".join(log_lines) + "\n",
        )
        deployment_run.logs_ref = logs_ref
        deployment_run.finished_at = datetime.now(timezone.utc)
        db.commit()
