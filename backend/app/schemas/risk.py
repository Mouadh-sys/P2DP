from pydantic import BaseModel


class RiskAssessmentRead(BaseModel):
    env_id: int
    score: int
    risk_class: str
    factors: dict[str, int]
