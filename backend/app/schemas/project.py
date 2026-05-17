import uuid

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: uuid.UUID
    owner_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
