import uuid

from pydantic import BaseModel, ConfigDict


class FindingRead(BaseModel):
    id: uuid.UUID
    env_id: uuid.UUID
    layer: str
    engine: str
    rule_id: str
    severity: str
    resource: str
    evidence: str | None = None
    recommendation: str | None = None

    model_config = ConfigDict(from_attributes=True)
