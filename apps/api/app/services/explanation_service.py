"""First real AI Gateway consumer (ADR-015). Generates a short worked
explanation for a Physics skill. Never touches PDE — no import of
decision_policy, authorization_service, decision_engine_service, or
Decision anywhere in this module (ADR-015 §7).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.ai.prompts import SKILL_EXPLANATION_V1
from app.models.ai_usage import AIUsageCapability
from app.models.curriculum import Skill
from app.schemas.ai import ExplanationResponse


class ExplanationError(Exception):
    pass


class SkillNotFound(ExplanationError):
    pass


def generate_skill_explanation(
    db: Session, *, gateway: AIGateway, tenant_id: str, actor_user_id: str, skill_id: str
) -> ExplanationResponse:
    # Skill is shared curriculum reference data, not tenant-owned (see
    # app/models/curriculum.py) — no tenant filter on the lookup itself,
    # matching curriculum_service's existing precedent. Tenant scoping
    # applies only to the AIUsageRecord this call writes.
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise SkillNotFound()

    result = gateway.generate(
        template=SKILL_EXPLANATION_V1,
        prompt_kwargs={"skill_name": skill.name, "skill_description": skill.description or ""},
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        capability=AIUsageCapability.SKILL_EXPLANATION,
    )

    return ExplanationResponse(
        skill_id=skill.id,
        explanation=result.explanation,
        key_points=result.key_points,
        provider=gateway.provider.provider_name,
        model=gateway.provider.model_name,
        prompt_name=SKILL_EXPLANATION_V1.name,
        prompt_version=SKILL_EXPLANATION_V1.version,
        generated_at=datetime.now(timezone.utc),
    )
