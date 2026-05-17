from pydantic import BaseModel


class FindingRead(BaseModel):
    id: int
    env_id: int
    layer: str
    engine: str
    severity: str
    resource: str
    recommendation: str
