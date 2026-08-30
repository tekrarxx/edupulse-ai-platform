"""§99 reproducibility check for LOAD-TEST.md's diagnosed bottleneck fix
(ADR-012's facet-independence assumption, batched in
`knowledge_state_service.get_knowledge_states_for_skill`). The batched
path and the original per-facet path must produce bit-identical results
for identical data — not merely similar — since both call the exact same
pure `compute_knowledge_state` and the exact same `_apply_result_to_state`
field-copying helper; this test proves that refactor didn't silently
change either one.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.curriculum import Concept, Skill, SkillFacetType, Subject, Topic
from app.models.evidence import Evidence, EvidenceDirectness, EvidencePolarity
from app.models.observation import Observation, ObservationEventType
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User
from app.services import knowledge_state_service


def _seed_tenant_student_skill(db: Session) -> tuple[str, str, str]:
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    student = User(
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash="irrelevant-for-this-test",
        display_name="Student",
        role=Role.STUDENT,
    )
    db.add(student)
    db.flush()
    db.commit()
    return tenant.id, student.id, str(uuid.uuid4())


def _add_evidence(db: Session, *, tenant_id: str, student_id: str, skill_id: str, facet_type: SkillFacetType, polarity: EvidencePolarity) -> None:
    observation = Observation(
        tenant_id=tenant_id,
        subject_type="attempt",
        subject_id=str(uuid.uuid4()),
        event_type=ObservationEventType.ANSWER_CORRECT if polarity == EvidencePolarity.POSITIVE else ObservationEventType.ANSWER_INCORRECT,
        payload={},
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(observation)
    db.flush()
    db.add(
        Evidence(
            tenant_id=tenant_id,
            student_user_id=student_id,
            observation_id=observation.id,
            skill_id=skill_id,
            facet_type=facet_type,
            polarity=polarity,
            directness=EvidenceDirectness.DIRECT,
            reliability=1.0,
            task_validity=1.0,
            transfer_relevance=False,
            evaluation_confidence=1.0,
        )
    )
    db.commit()


def test_batched_and_per_facet_paths_produce_identical_results(db: Session) -> None:
    tenant_id, student_id, skill_id = _seed_tenant_student_skill(db)
    # Real curriculum row needed since both code paths under test call
    # db.get(Skill, skill_id) and raise SkillNotFound otherwise.
    subject = Subject(slug=f"s-{uuid.uuid4().hex[:8]}", name="S")
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="t", name="T")
    db.add(topic)
    db.flush()
    concept = Concept(topic_id=topic.id, slug="c", name="C")
    db.add(concept)
    db.flush()
    skill = Skill(id=skill_id, concept_id=concept.id, slug="sk", name="Skill")
    db.add(skill)
    db.commit()

    # Uneven, realistic evidence across facets — APPLICATION gets several
    # mixed-polarity rows, others get one or zero, to exercise every branch
    # (insufficient/low/high confidence) in one test.
    _add_evidence(db, tenant_id=tenant_id, student_id=student_id, skill_id=skill_id, facet_type=SkillFacetType.APPLICATION, polarity=EvidencePolarity.POSITIVE)
    _add_evidence(db, tenant_id=tenant_id, student_id=student_id, skill_id=skill_id, facet_type=SkillFacetType.APPLICATION, polarity=EvidencePolarity.POSITIVE)
    _add_evidence(db, tenant_id=tenant_id, student_id=student_id, skill_id=skill_id, facet_type=SkillFacetType.APPLICATION, polarity=EvidencePolarity.NEGATIVE)
    _add_evidence(db, tenant_id=tenant_id, student_id=student_id, skill_id=skill_id, facet_type=SkillFacetType.TRANSFER, polarity=EvidencePolarity.NEGATIVE)
    # RECOGNITION, RECALL, RETENTION intentionally get zero evidence rows.

    as_of = datetime(2026, 8, 30, tzinfo=timezone.utc)

    per_facet_results = {
        facet_type: knowledge_state_service.get_or_recompute_knowledge_state(
            db, tenant_id=tenant_id, student_user_id=student_id, skill_id=skill_id, facet_type=facet_type, as_of=as_of
        )
        for facet_type in SkillFacetType
    }
    batched_results = {
        state.facet_type: state
        for state in knowledge_state_service.get_knowledge_states_for_skill(
            db, tenant_id=tenant_id, student_user_id=student_id, skill_id=skill_id, as_of=as_of
        )
    }

    assert set(per_facet_results) == set(batched_results) == set(SkillFacetType)
    for facet_type in SkillFacetType:
        per_facet = per_facet_results[facet_type]
        batched = batched_results[facet_type]
        assert batched.alpha == per_facet.alpha
        assert batched.beta == per_facet.beta
        assert batched.mastery_probability == per_facet.mastery_probability
        assert batched.confidence_label == per_facet.confidence_label
        assert batched.effective_n == per_facet.effective_n
        assert batched.variance == per_facet.variance
        assert batched.evidence_count == per_facet.evidence_count
        assert batched.model_version == per_facet.model_version
        assert batched.as_of == per_facet.as_of
