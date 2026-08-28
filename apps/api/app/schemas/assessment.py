from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.assessment import AssessmentType, EvaluationMethod
from app.models.curriculum import SkillFacetType
from app.models.evidence import EvidenceDirectness, EvidencePolarity
from app.models.observation import ObservationEventType

# Keys that would smuggle an interpreted conclusion into a supposedly raw
# Observation payload (§22, §26). Closed off at the schema boundary — this
# is one half of "an observation cannot carry an interpreted conclusion,"
# the other half being event_type's closed enum (see Observation model).
_INTERPRETIVE_PAYLOAD_KEYS = {
    "mastery",
    "conclusion",
    "understands",
    "knows",
    "proficiency",
    "skill_level",
    "misconception",
    "interpretation",
}

ObservationPayloadValue = str | int | float | bool


class QuestionCreate(BaseModel):
    skill_id: str
    facet_type: SkillFacetType
    prompt: str = Field(min_length=1)
    correct_answer: str | None = None
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)


class QuestionOut(BaseModel):
    """Admin-facing — includes the answer key. Never returned from a
    student-readable endpoint (see QuestionPublicOut)."""

    id: str
    skill_id: str
    facet_type: SkillFacetType
    prompt: str
    correct_answer: str | None
    difficulty: float
    content_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionPublicOut(BaseModel):
    id: str
    skill_id: str
    facet_type: SkillFacetType
    prompt: str
    difficulty: float
    content_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmitAttemptRequest(BaseModel):
    question_id: str
    assessment_type: AssessmentType
    learner_response: str
    idempotency_key: str = Field(min_length=1, max_length=100)


class AttemptOut(BaseModel):
    id: str
    question_id: str
    assessment_type: AssessmentType
    is_correct: bool | None
    evaluation_method: EvaluationMethod | None
    evaluation_confidence: float | None
    submitted_at: datetime
    evaluated_at: datetime | None

    model_config = {"from_attributes": True}


class EvaluateAttemptRequest(BaseModel):
    is_correct: bool
    evaluation_confidence: float = Field(ge=0.0, le=1.0)


class ObservationCreate(BaseModel):
    subject_type: str = Field(min_length=1, max_length=50)
    subject_id: str = Field(min_length=1, max_length=36)
    event_type: ObservationEventType
    payload: dict[str, ObservationPayloadValue] = Field(default_factory=dict)
    correlation_id: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=100)

    @field_validator("payload")
    @classmethod
    def _reject_interpretive_keys(cls, value: dict) -> dict:
        found = _INTERPRETIVE_PAYLOAD_KEYS & value.keys()
        if found:
            raise ValueError(f"payload cannot contain interpreted-conclusion keys: {sorted(found)}")
        return value


class ObservationOut(BaseModel):
    id: str
    subject_type: str
    subject_id: str
    event_type: ObservationEventType
    payload: dict
    correlation_id: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    id: str
    student_user_id: str
    observation_id: str
    skill_id: str
    facet_type: SkillFacetType
    polarity: EvidencePolarity
    directness: EvidenceDirectness
    reliability: float
    task_validity: float
    transfer_relevance: bool
    evaluation_confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}
