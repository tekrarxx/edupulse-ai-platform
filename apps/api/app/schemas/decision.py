from datetime import datetime

from pydantic import BaseModel

from app.models.assessment import AssessmentType
from app.models.decision import AuthorizationResult, CandidateActionType, ReasonCode


class CandidateActionScoreOut(BaseModel):
    action: CandidateActionType
    score: float
    reason_codes: list[ReasonCode]


class KnowledgeStateSnapshotEntry(BaseModel):
    facet_type: str
    mastery_probability: float
    confidence_label: str
    evidence_count: int
    model_version: str
    as_of: str


class DecisionOut(BaseModel):
    id: str
    student_user_id: str
    skill_id: str
    selected_action: CandidateActionType
    candidate_actions: list[CandidateActionScoreOut]
    reason_codes: list[ReasonCode]
    policy_version: str
    model_version: str
    confidence: float
    knowledge_state_snapshot: list[KnowledgeStateSnapshotEntry]
    evidence_ids: list[str]
    authorization_result: AuthorizationResult
    authorization_reason: str
    is_shadow: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    """The execution layer (§113 P8+): a real Question resolved from a
    Decision's selected_action, for a student to actually answer — never a
    fabricated prompt (§105). `correct_answer` is deliberately absent, same
    as QuestionPublicOut (app/schemas/assessment.py)."""

    decision_id: str
    skill_id: str
    skill_name: str
    selected_action: CandidateActionType
    assessment_type: AssessmentType
    question_id: str
    prompt: str
    difficulty: float

    model_config = {"from_attributes": True}
