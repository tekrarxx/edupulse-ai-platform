from datetime import datetime

from pydantic import BaseModel, Field

from app.models.knowledge_state import ConfidenceLabel
from app.models.retention import HypothesisVerdict, RetentionCheckpointStatus


class HypothesisOut(BaseModel):
    predicted_mastery_probability: float
    predicted_confidence_label: ConfidenceLabel
    predicted_at: datetime
    evaluated_at: datetime | None
    actual_is_correct: bool | None
    verdict: HypothesisVerdict

    model_config = {"from_attributes": True}


class RetentionCheckpointOut(BaseModel):
    id: str
    student_user_id: str
    skill_id: str
    checkpoint_days: int
    origin_evidence_id: str
    scheduled_for: datetime
    status: RetentionCheckpointStatus
    delayed_attempt_id: str | None
    retention_estimate: float | None
    model_version: str
    created_at: datetime
    hypothesis: HypothesisOut | None

    model_config = {"from_attributes": True}


class CompleteCheckpointRequest(BaseModel):
    question_id: str
    learner_response: str
    idempotency_key: str = Field(min_length=1, max_length=100)
