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
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.curriculum import Skill, SkillFacetType
from app.models.decision import CandidateActionType, Decision
from app.models.knowledge_state import ConfidenceLabel, KnowledgeState
from app.models.retention import RetentionCheckpoint, RetentionCheckpointStatus

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
