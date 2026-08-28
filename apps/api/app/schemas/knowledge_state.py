from datetime import datetime

from pydantic import BaseModel

from app.models.curriculum import SkillFacetType
from app.models.knowledge_state import ConfidenceLabel


class KnowledgeStateOut(BaseModel):
    """§26 enforcement point: `mastery_probability` never appears without
    `confidence_label` alongside it. `alpha`/`beta`/`variance` are
    deliberately not exposed here — they are internal/debugging fields
    (ADR-012); a client should read mastery through the labeled vocabulary,
    not raw posterior parameters."""

    student_user_id: str
    skill_id: str
    facet_type: SkillFacetType
    mastery_probability: float
    confidence_label: ConfidenceLabel
    effective_n: float
    evidence_count: int
    model_version: str
    as_of: datetime

    model_config = {"from_attributes": True}
