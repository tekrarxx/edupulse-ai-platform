"""Execution layer (§113 P8+, task_service.py) — the Decision -> Question
resolution logic in isolation from the full PDE scoring pass. Constructs
Decision rows directly rather than going through decision_engine_service,
since only selected_action/authorization_result/is_shadow matter here.
"""
import uuid

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.assessment import AssessmentType, Attempt, Question
from app.models.curriculum import Concept, Skill, SkillFacetType, Subject, Topic
from app.models.decision import AuthorizationResult, CandidateActionType, Decision
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User
from app.services import task_service


def _make_tenant_and_student(db: Session) -> tuple[Tenant, User]:
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    student = User(
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="Test Student",
        role=Role.STUDENT,
    )
    db.add(student)
    db.commit()
    return tenant, student


def _make_skill(db: Session) -> Skill:
    subject = Subject(slug=f"s-{uuid.uuid4().hex[:8]}", name="S")
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="t", name="T")
    db.add(topic)
    db.flush()
    concept = Concept(topic_id=topic.id, slug="c", name="C")
    db.add(concept)
    db.flush()
    skill = Skill(concept_id=concept.id, slug="sk", name="Skill")
    db.add(skill)
    db.commit()
    return skill


def _make_decision(
    db: Session,
    *,
    tenant: Tenant,
    student: User,
    skill: Skill,
    selected_action: CandidateActionType,
    authorization_result: AuthorizationResult = AuthorizationResult.ALLOWED,
    is_shadow: bool = False,
) -> Decision:
    decision = Decision(
        tenant_id=tenant.id,
        student_user_id=student.id,
        skill_id=skill.id,
        selected_action=selected_action,
        candidate_actions=[],
        reason_codes=[],
        policy_version="pde-policy-v1",
        model_version="bayesian-beta-binomial-v1",
        confidence=0.5,
        knowledge_state_snapshot=[],
        evidence_ids=[],
        authorization_result=authorization_result,
        authorization_reason="test",
        is_shadow=is_shadow,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def _make_question(db: Session, *, skill: Skill, facet_type: SkillFacetType, prompt: str, difficulty: float = 0.5) -> Question:
    question = Question(skill_id=skill.id, facet_type=facet_type, prompt=prompt, correct_answer="x", difficulty=difficulty)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def test_resolves_a_real_question_for_a_task_resolvable_action(db: Session) -> None:
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    _make_question(db, skill=skill, facet_type=SkillFacetType.TRANSFER, prompt="Transfer question")
    decision = _make_decision(db, tenant=tenant, student=student, skill=skill, selected_action=CandidateActionType.TRANSFER_TASK)

    task = task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)

    assert task.decision_id == decision.id
    assert task.prompt == "Transfer question"
    assert task.assessment_type == AssessmentType.TRANSFER


def test_raises_action_has_no_task_for_a_non_question_action(db: Session) -> None:
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    decision = _make_decision(db, tenant=tenant, student=student, skill=skill, selected_action=CandidateActionType.HINT)

    try:
        task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)
        assert False, "expected ActionHasNoTask"
    except task_service.ActionHasNoTask:
        pass


def test_raises_no_question_available_when_none_exists_for_the_facet(db: Session) -> None:
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    decision = _make_decision(db, tenant=tenant, student=student, skill=skill, selected_action=CandidateActionType.RETRIEVAL_QUESTION)

    try:
        task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)
        assert False, "expected NoQuestionAvailable"
    except task_service.NoQuestionAvailable:
        pass


def test_raises_decision_not_executable_for_an_escalated_decision(db: Session) -> None:
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    _make_question(db, skill=skill, facet_type=SkillFacetType.APPLICATION, prompt="Q")
    decision = _make_decision(
        db,
        tenant=tenant,
        student=student,
        skill=skill,
        selected_action=CandidateActionType.EASIER_TASK,
        authorization_result=AuthorizationResult.ESCALATED,
    )

    try:
        task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)
        assert False, "expected DecisionNotExecutable"
    except task_service.DecisionNotExecutable:
        pass


def test_raises_decision_not_executable_for_a_shadow_decision(db: Session) -> None:
    """§38: a shadow decision must never surface a real task."""
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    _make_question(db, skill=skill, facet_type=SkillFacetType.APPLICATION, prompt="Q")
    decision = _make_decision(
        db, tenant=tenant, student=student, skill=skill, selected_action=CandidateActionType.EASIER_TASK, is_shadow=True
    )

    try:
        task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)
        assert False, "expected DecisionNotExecutable"
    except task_service.DecisionNotExecutable:
        pass


def test_prefers_an_unattempted_question_over_a_repeat(db: Session) -> None:
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    attempted = _make_question(db, skill=skill, facet_type=SkillFacetType.APPLICATION, prompt="Already attempted")
    fresh = _make_question(db, skill=skill, facet_type=SkillFacetType.APPLICATION, prompt="Fresh")
    db.add(
        Attempt(
            tenant_id=tenant.id,
            student_user_id=student.id,
            question_id=attempted.id,
            assessment_type=AssessmentType.FORMATIVE,
            question_content_version=1,
            learner_response="x",
            idempotency_key=str(uuid.uuid4()),
        )
    )
    db.commit()
    decision = _make_decision(db, tenant=tenant, student=student, skill=skill, selected_action=CandidateActionType.REVIEW_TASK)

    task = task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)

    # REVIEW_TASK is the one deliberate exception (its whole point is
    # repeating known content) — it takes the first-created candidate
    # regardless, even with an unattempted alternative (`fresh`) available.
    assert task.question_id == attempted.id
    assert fresh.id != task.question_id


def test_non_review_action_prefers_unattempted_question(db: Session) -> None:
    tenant, student = _make_tenant_and_student(db)
    skill = _make_skill(db)
    attempted = _make_question(db, skill=skill, facet_type=SkillFacetType.APPLICATION, prompt="Already attempted")
    fresh = _make_question(db, skill=skill, facet_type=SkillFacetType.APPLICATION, prompt="Fresh")
    db.add(
        Attempt(
            tenant_id=tenant.id,
            student_user_id=student.id,
            question_id=attempted.id,
            assessment_type=AssessmentType.FORMATIVE,
            question_content_version=1,
            learner_response="x",
            idempotency_key=str(uuid.uuid4()),
        )
    )
    db.commit()
    decision = _make_decision(db, tenant=tenant, student=student, skill=skill, selected_action=CandidateActionType.EASIER_TASK)

    task = task_service.resolve_task_for_decision(db, tenant_id=tenant.id, decision_id=decision.id)

    assert task.question_id == fresh.id
