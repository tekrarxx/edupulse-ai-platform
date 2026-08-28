from datetime import datetime

from pydantic import BaseModel


class ExplanationRequest(BaseModel):
    skill_id: str


class ExplanationResponse(BaseModel):
    skill_id: str
    explanation: str
    key_points: list[str]
    provider: str
    model: str
    prompt_name: str
    prompt_version: str
    generated_at: datetime
