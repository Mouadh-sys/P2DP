import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RiskFactorDetail(BaseModel):
    key: str
    label: str
    weight: int
    contribution: int
    impact: str
    recommendation: str
    findings: list[str] = Field(default_factory=list)


class RiskAssessmentRead(BaseModel):
    id: uuid.UUID
    env_id: uuid.UUID
    score: float
    risk_class: str
    factors: list[RiskFactorDetail]
    top_factors: list[RiskFactorDetail]
    recommendations: list[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
