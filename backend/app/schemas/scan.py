import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanQueuedResponse(BaseModel):
    scan_id: uuid.UUID
    task_id: str
    status: str


class ScanStatusRead(BaseModel):
    id: uuid.UUID
    template_version_id: uuid.UUID
    env_id: uuid.UUID
    status: str
    task_id: str | None = None
    error_message: str | None = None
    findings_count: int = 0
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
