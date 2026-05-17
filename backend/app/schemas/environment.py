import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EnvironmentBase(BaseModel):
    target: Literal["dev", "local-k8s"] = "local-k8s"
    status: str = Field(default="pending", min_length=1, max_length=50)


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentRead(EnvironmentBase):
    id: uuid.UUID
    project_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
