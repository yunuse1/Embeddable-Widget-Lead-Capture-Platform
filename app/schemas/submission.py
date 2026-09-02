from typing import Any

from pydantic import BaseModel, Field


class SubmissionRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    honeypot: str = Field(default="", max_length=200)


class SubmissionResponse(BaseModel):
    id: int
    status: str
