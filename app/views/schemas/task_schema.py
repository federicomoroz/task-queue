from datetime import datetime

from pydantic import BaseModel, Field


class TaskIn(BaseModel):
    type: str = Field(..., examples=["echo", "http_request"])
    queue: str = Field("default", examples=["default", "high"])
    payload: dict = Field(default_factory=dict)
    max_retries: int = Field(3, ge=0, le=10)


class TaskOut(BaseModel):
    id: int
    type: str
    queue: str
    payload: str
    status: str
    max_retries: int
    retry_count: int
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueOut(BaseModel):
    name: str
    depth: int
