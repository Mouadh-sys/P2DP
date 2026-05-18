from pydantic import BaseModel


class ValidationQueuedResponse(BaseModel):
    task_id: str
    status: str = "queued"
