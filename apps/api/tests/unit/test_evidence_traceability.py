import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.curriculum import SkillFacetType
from app.models.evidence import Evidence, EvidenceDirectness, EvidencePolarity
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def test_evidence_cannot_be_created_without_an_observation(db: Session) -> None:
    """§23: Evidence always traces to an Observation. observation_id is a
    required (non-nullable) FK — this is the database backstop behind the
    fact that assessment_service.evaluate_attempt is the only code path that
    creates Evidence, and it always creates the Observation first."""
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    student = User(
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash="irrelevant",
        display_name="Student",
        role=Role.STUDENT,
    )
    db.add(student)
    db.flush()

    evidence = Evidence(
        tenant_id=tenant.id,
        student_user_id=student.id,
        observation_id=None,  # type: ignore[arg-type]
        skill_id=str(uuid.uuid4()),
        facet_type=SkillFacetType.APPLICATION,
        polarity=EvidencePolarity.POSITIVE,
        directness=EvidenceDirectness.DIRECT,
        reliability=1.0,
        task_validity=1.0,
        transfer_relevance=False,
        evaluation_confidence=1.0,
    )
    db.add(evidence)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
