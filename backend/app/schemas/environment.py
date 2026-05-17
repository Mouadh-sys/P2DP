from pydantic import BaseModel


class EnvironmentBase(BaseModel):
    project_id: int
    target: str = "local-k8s"


class EnvironmentRead(EnvironmentBase):
    id: int
    status: str = "pending"
