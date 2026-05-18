import uuid

from pydantic import BaseModel


class ReportCreated(BaseModel):
    report_id: uuid.UUID
    env_id: uuid.UUID
    download_url: str
