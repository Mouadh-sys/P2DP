import uuid

from pydantic import BaseModel, ConfigDict, Field


class EnvironmentBase(BaseModel):
    target: str = Field(default="local-k8s", min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=50)


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentRead(EnvironmentBase):
    id: uuid.UUID
    project_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
