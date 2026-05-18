import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArtifactRead(BaseModel):
    id: uuid.UUID
    template_version_id: uuid.UUID
    type: str
    storage_ref: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
