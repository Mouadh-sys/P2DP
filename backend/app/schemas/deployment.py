import uuid
from datetime import datetime

from pydantic import BaseModel

from app.db.models import DeploymentRun


class DeploymentRunRead(BaseModel):
    deployment_id: uuid.UUID
    env_id: uuid.UUID
    status: str
    git_commit: str | None = None
    trace_id: str | None = None
    logs_ref: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


def to_deployment_read(run: DeploymentRun) -> DeploymentRunRead:
    return DeploymentRunRead(
        deployment_id=run.id,
        env_id=run.env_id,
        status=run.status,
        git_commit=run.git_commit,
        trace_id=run.trace_id,
        logs_ref=run.logs_ref,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
