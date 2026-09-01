"""Student dashboard aggregation (§75, §18, §26). Read-only — composes
existing Phase 5-7 data (KnowledgeState, Decision, RetentionCheckpoint), no
new domain logic, no new writes. Never exposes a raw mastery_probability
float or an internal enum value to the student — every number is translated
to a plain-language label first (§26 language discipline extended to the
student-facing UI, not just the API's confidence_label vocabulary).

Knowledge state shown here is the last-computed cached value (whatever the
most recent `GET /knowledge-state` or `/decisions/next-action` call left in
the `knowledge_states` table for that skill) — this dashboard does not
recompute all of a student's skills on every page load, which would be an
unbounded-cost operation as their skill count grows. This is a deliberate
choice, not a staleness bug: a skill's cached state only goes stale between
a learning event and the next time anything queries it, and evidence
submission itself triggers a recompute for the APPLICATION facet (see
assessment_service._apply_evaluation -> retention_service.maybe_schedule_checkpoints,
which calls get_or_recompute_knowledge_state).
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsageRecord
from app.models.curriculum import Skill, SkillFacetType
from app.models.decision import AuthorizationResult, CandidateActionType, Decision
from app.models.evidence import Evidence, FailureMode
from app.models.knowledge_state import ConfidenceLabel, KnowledgeState
from app.models.plan import Plan
from app.models.relationship import TeacherStudentLink
from app.models.retention import Hypothesis, HypothesisVerdict, RetentionCheckpoint, RetentionCheckpointStatus
from app.models.tenant import Tenant
from app.models.user import Role, User
from app.services import entitlement_service

_ACTION_LABELS: dict[CandidateActionType, str] = {
    CandidateActionType.INSUFFICIENT_EVIDENCE_ACTION: "Bilgini ölçmek için birkaç soru çöz",
    CandidateActionType.RETRIEVAL_QUESTION: "Hatırlama alıştırması yap",
    CandidateActionType.NEW_CONCEPT_EXPLANATION: "Konuyu yeniden gözden geçir",
    CandidateActionType.EASIER_TASK: "Daha kolay bir görevle devam et",
    CandidateActionType.HARDER_TASK: "Daha zor bir görevi dene",
    CandidateActionType.TRANSFER_TASK: "Bildiğini farklı bir bağlamda uygula",
    CandidateActionType.REVIEW_TASK: "Bu konuyu tekrar et",
    CandidateActionType.DELAYED_RETENTION_ASSESSMENT: "Hatırladığını kontrol et",
    CandidateActionType.HINT: "İpucuyla devam et",
    CandidateActionType.WORKED_EXAMPLE: "Çözümlü örneğe bak",
    CandidateActionType.TEACHER_INTERVENTION: "Öğretmenine danış",
    CandidateActionType.DEFER_DECISION: "Şimdilik bekle",
}


@dataclass(frozen=True)
class SkillProgress:
    skill_id: str
    skill_name: str
    mastery_label: str
    is_weak: bool
    is_strong: bool
    next_action_label: str | None
    pending_retention_checkpoints: int


@dataclass(frozen=True)
class StudentDashboard:
    student_user_id: str
    skills: list[SkillProgress]
    weak_skill_count: int
    strong_skill_count: int
    upcoming_retention_count: int


def _mastery_label(state: KnowledgeState | None) -> tuple[str, bool, bool]:
    """Returns (label, is_weak, is_strong) — never a bare number (§26, §75)."""
    if state is None or state.confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE:
        return "Henüz yeterli veri yok", False, False
    if state.confidence_label == ConfidenceLabel.HIGH_CONFIDENCE and state.mastery_probability >= 0.75:
        return "İyi öğreniyorsun", False, True
    if state.mastery_probability < 0.4:
        return "Biraz daha çalış", True, False
    return "Devam ediyorsun", False, False


def get_student_dashboard(db: Session, *, tenant_id: str, student_user_id: str) -> StudentDashboard:
    knowledge_states = (
        db.query(KnowledgeState)
        .filter(
            KnowledgeState.tenant_id == tenant_id,
            KnowledgeState.student_user_id == student_user_id,
            KnowledgeState.facet_type == SkillFacetType.APPLICATION,
        )
        .all()
    )
    knowledge_state_by_skill = {ks.skill_id: ks for ks in knowledge_states}

    latest_decision_by_skill: dict[str, Decision] = {}
    decisions = (
        db.query(Decision)
        .filter(Decision.tenant_id == tenant_id, Decision.student_user_id == student_user_id, Decision.is_shadow.is_(False))
        .order_by(Decision.created_at.desc())
        .all()
    )
    for decision in decisions:
        latest_decision_by_skill.setdefault(decision.skill_id, decision)

    pending_checkpoints = (
        db.query(RetentionCheckpoint)
        .filter(
            RetentionCheckpoint.tenant_id == tenant_id,
            RetentionCheckpoint.student_user_id == student_user_id,
            RetentionCheckpoint.status == RetentionCheckpointStatus.PENDING,
        )
        .all()
    )
    pending_count_by_skill: dict[str, int] = {}
    for checkpoint in pending_checkpoints:
        pending_count_by_skill[checkpoint.skill_id] = pending_count_by_skill.get(checkpoint.skill_id, 0) + 1

    skill_ids = set(knowledge_state_by_skill) | set(latest_decision_by_skill) | set(pending_count_by_skill)
    skills_by_id = {s.id: s for s in db.query(Skill).filter(Skill.id.in_(skill_ids)).all()} if skill_ids else {}

    progress: list[SkillProgress] = []
    weak_count = 0
    strong_count = 0
    for skill_id in skill_ids:
        skill = skills_by_id.get(skill_id)
        if skill is None:
            continue
        state = knowledge_state_by_skill.get(skill_id)
        label, is_weak, is_strong = _mastery_label(state)
        if is_weak:
            weak_count += 1
        if is_strong:
            strong_count += 1

        decision = latest_decision_by_skill.get(skill_id)
        action_label = _ACTION_LABELS.get(decision.selected_action) if decision is not None else None

        progress.append(
            SkillProgress(
                skill_id=skill_id,
                skill_name=skill.name,
                mastery_label=label,
                is_weak=is_weak,
                is_strong=is_strong,
                next_action_label=action_label,
                pending_retention_checkpoints=pending_count_by_skill.get(skill_id, 0),
            )
        )

    progress.sort(key=lambda p: p.skill_name)

    return StudentDashboard(
        student_user_id=student_user_id,
        skills=progress,
        weak_skill_count=weak_count,
        strong_skill_count=strong_count,
        upcoming_retention_count=len(pending_checkpoints),
    )


# --- Teacher dashboard (§76) ---
#
# Scoped to the requesting teacher's own students via TeacherStudentLink
# (§80 "do not expose unnecessary sensitive learner information") — not
# every student in the tenant. A tenant-wide view belongs to the Admin
# Dashboard (a separate slice), not this one.
#
# Every one of §76's six questions is answered from a real, already-computed
# signal, never a fabricated heuristic:
#   - "needs attention"   -> a weak skill, a NOT_SUPPORTED retention verdict,
#                             or a Decision that was actually ESCALATED by
#                             the PDE's own authorization step (Phase 6) —
#                             Prometheus already said "a human should look
#                             at this."
#   - "weak skills"        -> the same mastery-label classification the
#                             student dashboard uses.
#   - "improving"           -> compares the APPLICATION mastery in the
#                             earliest vs. latest real Decision's
#                             knowledge_state_snapshot for that skill
#                             (Decisions are append-only and timestamped —
#                             a genuine trend, not an invented one).
#   - "forgetting"          -> a completed RetentionCheckpoint whose
#                             Hypothesis verdict is NOT_SUPPORTED (Phase 7's
#                             falsification framework existing for exactly
#                             this purpose).
#   - "misconceptions"      -> Evidence.failure_mode == MISCONCEPTION
#                             (teacher-classified, per Phase 7/§31).
#   - "what should I do next" -> the latest decision's action label.

_IMPROVEMENT_MARGIN = 0.1


@dataclass(frozen=True)
class StudentSummary:
    student_user_id: str
    student_name: str
    needs_attention: bool
    attention_reasons: list[str] = field(default_factory=list)
    weak_skill_names: list[str] = field(default_factory=list)
    improving_skill_names: list[str] = field(default_factory=list)
    forgetting_skill_names: list[str] = field(default_factory=list)
    misconception_skill_names: list[str] = field(default_factory=list)
    next_action_label: str | None = None


@dataclass(frozen=True)
class TeacherDashboard:
    students: list[StudentSummary]
    students_needing_attention_count: int


def _application_mastery(snapshot: list[dict]) -> float | None:
    for entry in snapshot:
        if entry.get("facet_type") == SkillFacetType.APPLICATION.value:
            return entry.get("mastery_probability")
    return None


def _summarize_student(db: Session, *, tenant_id: str, student: User) -> StudentSummary:
    knowledge_states = (
        db.query(KnowledgeState)
        .filter(
            KnowledgeState.tenant_id == tenant_id,
            KnowledgeState.student_user_id == student.id,
            KnowledgeState.facet_type == SkillFacetType.APPLICATION,
        )
        .all()
    )
    weak_skill_ids = {ks.skill_id for ks in knowledge_states if _mastery_label(ks)[1]}

    decisions = (
        db.query(Decision)
        .filter(Decision.tenant_id == tenant_id, Decision.student_user_id == student.id, Decision.is_shadow.is_(False))
        .order_by(Decision.created_at.asc())
        .all()
    )
    first_decision_by_skill: dict[str, Decision] = {}
    last_decision_by_skill: dict[str, Decision] = {}
    escalated_skill_ids: set[str] = set()
    for decision in decisions:
        first_decision_by_skill.setdefault(decision.skill_id, decision)
        last_decision_by_skill[decision.skill_id] = decision
        if decision.authorization_result == AuthorizationResult.ESCALATED:
            escalated_skill_ids.add(decision.skill_id)

    improving_skill_ids: set[str] = set()
    for skill_id, first in first_decision_by_skill.items():
        last = last_decision_by_skill[skill_id]
        if first.id == last.id:
            continue
        first_mastery = _application_mastery(first.knowledge_state_snapshot)
        last_mastery = _application_mastery(last.knowledge_state_snapshot)
        if first_mastery is not None and last_mastery is not None and last_mastery - first_mastery >= _IMPROVEMENT_MARGIN:
            improving_skill_ids.add(skill_id)

    forgetting_skill_ids = {
        hyp.skill_id
        for hyp in db.query(Hypothesis)
        .filter(
            Hypothesis.tenant_id == tenant_id,
            Hypothesis.student_user_id == student.id,
            Hypothesis.verdict == HypothesisVerdict.NOT_SUPPORTED,
        )
        .all()
    }

    misconception_skill_ids = {
        ev.skill_id
        for ev in db.query(Evidence)
        .filter(
            Evidence.tenant_id == tenant_id,
            Evidence.student_user_id == student.id,
            Evidence.failure_mode == FailureMode.MISCONCEPTION,
        )
        .all()
    }

    all_skill_ids = weak_skill_ids | improving_skill_ids | forgetting_skill_ids | misconception_skill_ids | escalated_skill_ids
    skills_by_id = {s.id: s for s in db.query(Skill).filter(Skill.id.in_(all_skill_ids)).all()} if all_skill_ids else {}

    def _names(ids: set[str]) -> list[str]:
        return sorted(skills_by_id[i].name for i in ids if i in skills_by_id)

    attention_reasons: list[str] = []
    if weak_skill_ids:
        attention_reasons.append("Zayıf beceriler var")
    if forgetting_skill_ids:
        attention_reasons.append("Hatırlama kontrolünü geçemedi")
    if escalated_skill_ids:
        attention_reasons.append("Sistem öğretmen incelemesi öneriyor")

    latest_overall_decision = max(decisions, key=lambda d: d.created_at) if decisions else None
    next_action_label = (
        _ACTION_LABELS.get(latest_overall_decision.selected_action) if latest_overall_decision is not None else None
    )

    return StudentSummary(
        student_user_id=student.id,
        student_name=student.display_name,
        needs_attention=bool(attention_reasons),
        attention_reasons=attention_reasons,
        weak_skill_names=_names(weak_skill_ids),
        improving_skill_names=_names(improving_skill_ids),
        forgetting_skill_names=_names(forgetting_skill_ids),
        misconception_skill_names=_names(misconception_skill_ids),
        next_action_label=next_action_label,
    )


def get_teacher_dashboard(db: Session, *, tenant_id: str, teacher_user_id: str) -> TeacherDashboard:
    linked_student_ids = [
        link.student_user_id
        for link in db.query(TeacherStudentLink)
        .filter(TeacherStudentLink.tenant_id == tenant_id, TeacherStudentLink.teacher_user_id == teacher_user_id)
        .all()
    ]
    if not linked_student_ids:
        return TeacherDashboard(students=[], students_needing_attention_count=0)

    students = db.query(User).filter(User.tenant_id == tenant_id, User.id.in_(linked_student_ids)).all()
    summaries = [_summarize_student(db, tenant_id=tenant_id, student=student) for student in students]
    summaries.sort(key=lambda s: (not s.needs_attention, s.student_name))

    return TeacherDashboard(
        students=summaries,
        students_needing_attention_count=sum(1 for s in summaries if s.needs_attention),
    )


# --- Admin dashboard (§77) ---
#
# Tenant-wide, not per-teacher-linked-students-only (that's the Teacher
# Dashboard above). §80 "do not expose unnecessary sensitive learner
# information" is honored by reporting *counts* only — no per-student names
# or reasons at this level, unlike the Teacher Dashboard which a teacher
# legitimately needs for individual intervention.
#
# §77 also asks for "subscription" — Plan/Subscription/Entitlement (§59-§61)
# do not exist in this codebase yet (that's a later phase), so this
# dashboard deliberately has no subscription field rather than fabricating
# one (§105 "No Fake Implementations"). The same applies to "adoption" in
# the multi-tenant-benchmarking sense — this reports this tenant's own
# activity only, not a cross-tenant comparison.
#
# "system health" here means the AI Gateway's own accounting (§45, §65,
# ADR-015) — the only subsystem in this codebase that can fail against an
# external dependency (Ollama) and record it. There is no separate
# infrastructure-health check (DB/Redis probes) in this phase; that belongs
# to §83 Observability, not this read-model.


@dataclass(frozen=True)
class AdminDashboard:
    tenant_id: str
    active_student_count: int
    active_teacher_count: int
    students_needing_attention_count: int
    weak_skill_student_count: int
    forgetting_student_count: int
    misconception_student_count: int
    escalated_student_count: int
    retention_pending_count: int
    retention_supported_count: int
    retention_not_supported_count: int
    retention_inconclusive_count: int
    decisions_total_count: int
    decisions_allowed_count: int
    decisions_escalated_count: int
    decisions_rejected_count: int
    ai_requests_total_count: int
    ai_requests_success_count: int
    ai_requests_failed_count: int
    plan_name: str
    ai_explanations_used_this_month: int
    # None = unlimited (ADR-016 — absence of a configured entitlement is
    # never a fabricated restriction).
    ai_explanations_monthly_limit: int | None
    tenant_user_count: int
    tenant_user_limit: int | None


def get_admin_dashboard(db: Session, *, tenant_id: str) -> AdminDashboard:
    students = db.query(User).filter(User.tenant_id == tenant_id, User.role == Role.STUDENT).all()
    active_student_count = sum(1 for s in students if s.is_active)
    active_teacher_count = (
        db.query(User).filter(User.tenant_id == tenant_id, User.role == Role.TEACHER, User.is_active.is_(True)).count()
    )

    summaries = [_summarize_student(db, tenant_id=tenant_id, student=student) for student in students]

    checkpoints = db.query(RetentionCheckpoint).filter(RetentionCheckpoint.tenant_id == tenant_id).all()
    retention_pending_count = sum(1 for c in checkpoints if c.status == RetentionCheckpointStatus.PENDING)

    hypotheses = db.query(Hypothesis).filter(Hypothesis.tenant_id == tenant_id).all()
    retention_supported_count = sum(1 for h in hypotheses if h.verdict == HypothesisVerdict.SUPPORTED)
    retention_not_supported_count = sum(1 for h in hypotheses if h.verdict == HypothesisVerdict.NOT_SUPPORTED)
    retention_inconclusive_count = sum(1 for h in hypotheses if h.verdict == HypothesisVerdict.INCONCLUSIVE)

    decisions = db.query(Decision).filter(Decision.tenant_id == tenant_id, Decision.is_shadow.is_(False)).all()
    decisions_allowed_count = sum(1 for d in decisions if d.authorization_result == AuthorizationResult.ALLOWED)
    decisions_escalated_count = sum(1 for d in decisions if d.authorization_result == AuthorizationResult.ESCALATED)
    decisions_rejected_count = sum(1 for d in decisions if d.authorization_result == AuthorizationResult.REJECTED)

    ai_records = db.query(AIUsageRecord).filter(AIUsageRecord.tenant_id == tenant_id).all()
    ai_requests_success_count = sum(1 for r in ai_records if r.success)

    tenant = db.get(Tenant, tenant_id)
    plan = db.get(Plan, tenant.plan_id) if tenant is not None and tenant.plan_id is not None else None
    plan_name = plan.name if plan is not None else "Free"  # matches entitlement_service's own null-plan_id fallback
    ai_explanations_used, ai_explanations_limit = entitlement_service.get_ai_explanation_usage(db, tenant_id=tenant_id)
    tenant_user_count, tenant_user_limit = entitlement_service.get_tenant_user_seat_usage(db, tenant_id=tenant_id)

    return AdminDashboard(
        tenant_id=tenant_id,
        active_student_count=active_student_count,
        active_teacher_count=active_teacher_count,
        students_needing_attention_count=sum(1 for s in summaries if s.needs_attention),
        weak_skill_student_count=sum(1 for s in summaries if s.weak_skill_names),
        forgetting_student_count=sum(1 for s in summaries if s.forgetting_skill_names),
        misconception_student_count=sum(1 for s in summaries if s.misconception_skill_names),
        escalated_student_count=sum(1 for s in summaries if "Sistem öğretmen incelemesi öneriyor" in s.attention_reasons),
        retention_pending_count=retention_pending_count,
        retention_supported_count=retention_supported_count,
        retention_not_supported_count=retention_not_supported_count,
        retention_inconclusive_count=retention_inconclusive_count,
        decisions_total_count=len(decisions),
        decisions_allowed_count=decisions_allowed_count,
        decisions_escalated_count=decisions_escalated_count,
        decisions_rejected_count=decisions_rejected_count,
        ai_requests_total_count=len(ai_records),
        ai_requests_success_count=ai_requests_success_count,
        ai_requests_failed_count=len(ai_records) - ai_requests_success_count,
        plan_name=plan_name,
        ai_explanations_used_this_month=ai_explanations_used,
        ai_explanations_monthly_limit=ai_explanations_limit,
        tenant_user_count=tenant_user_count,
        tenant_user_limit=tenant_user_limit,
    )
