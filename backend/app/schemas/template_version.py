import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TemplateVersionRead(BaseModel):
    id: uuid.UUID
    env_id: uuid.UUID
    files_ref: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
