import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict


class EnvironmentBase(BaseModel):
    target: Literal["dev", "local-k8s"]
    status: Literal["pending", "active", "failed"]


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentRead(EnvironmentBase):
    id: uuid.UUID
    project_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
