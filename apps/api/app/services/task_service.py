"""Execution layer (§113 P8+; this session's ROADMAP.md P1 item). Resolves
a Prometheus Decision's `selected_action` into a real, answerable Question
— the missing link between "the engine decided correctly" (Phase 6/PDE,
proven by MVP-GATE.md) and "a student experiences that decision" (the
dashboard previously only showed `next_action_label` as inert text, see
app/services/dashboard_service.py's `_ACTION_LABELS`).

This module reads Decision + Question but never writes either — the
student still submits their answer through the existing, unchanged
POST /assessment/attempts (app/services/assessment_service.py), which is
what actually creates the Attempt/Observation/Evidence chain. This module's
only job is "which question, for which decision" — it never invents
content (§105): every returned prompt is a real Question row a
teacher/script already created.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.assessment import AssessmentType, Attempt, Question
from app.models.curriculum import Skill, SkillFacetType
from app.models.decision import AuthorizationResult, CandidateActionType, Decision


class TaskError(Exception):
    pass


class DecisionNotExecutable(TaskError):
    """Escalated/rejected/shadow decisions never resolve to a task (§37):
    authorization is a separate gate from decision generation, and a
    decision that was not ALLOWED must not let the student self-execute
    around it. A shadow decision (§38) never affects the learner by
    definition — it must not surface a task either."""


class ActionHasNoTask(TaskError):
    """A structurally correct, deliberate fact, not a bug: some candidate
    actions are not question-answering activities (HINT, WORKED_EXAMPLE,
    NEW_CONCEPT_EXPLANATION, TEACHER_INTERVENTION, DEFER_DECISION).
    DELAYED_RETENTION_ASSESSMENT already has its own dedicated flow
    (GET /retention/checkpoints/due) and is deliberately excluded here too
    — one execution path per action type, not two competing ones."""


class NoQuestionAvailable(TaskError):
    """A genuine content gap, not a code bug: the action is task-resolvable
    in principle, but no Question exists yet for this skill+facet. Real,
    never silently hidden or fabricated (§105/§106)."""


@dataclass(frozen=True)
class ResolvedTask:
    decision_id: str
    skill_id: str
    skill_name: str
    selected_action: CandidateActionType
    assessment_type: AssessmentType
    question_id: str
    prompt: str
    difficulty: float


# Which SkillFacetType/AssessmentType a candidate action resolves to. Only
# actions that are genuinely "go answer a question of this kind" appear
# here — see ActionHasNoTask for why the rest are deliberately absent.
_ACTION_TASK_MAPPING: dict[CandidateActionType, tuple[SkillFacetType, AssessmentType]] = {
    CandidateActionType.INSUFFICIENT_EVIDENCE_ACTION: (SkillFacetType.APPLICATION, AssessmentType.DIAGNOSTIC),
    CandidateActionType.RETRIEVAL_QUESTION: (SkillFacetType.RECALL, AssessmentType.RETRIEVAL_PRACTICE),
    CandidateActionType.EASIER_TASK: (SkillFacetType.APPLICATION, AssessmentType.APPLICATION),
    CandidateActionType.HARDER_TASK: (SkillFacetType.APPLICATION, AssessmentType.APPLICATION),
    CandidateActionType.TRANSFER_TASK: (SkillFacetType.TRANSFER, AssessmentType.TRANSFER),
    CandidateActionType.REVIEW_TASK: (SkillFacetType.APPLICATION, AssessmentType.APPLICATION),
}


def resolve_task_for_decision(db: Session, *, tenant_id: str, decision_id: str) -> ResolvedTask:
    decision = db.get(Decision, decision_id)
    if decision is None or decision.tenant_id != tenant_id:
        raise TaskError("decision not found in this tenant")  # caller is expected to have already checked this

    if decision.is_shadow or decision.authorization_result != AuthorizationResult.ALLOWED:
        raise DecisionNotExecutable()

    mapping = _ACTION_TASK_MAPPING.get(decision.selected_action)
    if mapping is None:
        raise ActionHasNoTask()
    facet_type, assessment_type = mapping

    already_attempted_question_ids = {
        row[0]
        for row in db.query(Attempt.question_id)
        .join(Question, Question.id == Attempt.question_id)
        .filter(
            Attempt.tenant_id == tenant_id,
            Attempt.student_user_id == decision.student_user_id,
            Question.skill_id == decision.skill_id,
            Question.facet_type == facet_type,
        )
        .all()
    }

    query = db.query(Question).filter(Question.skill_id == decision.skill_id, Question.facet_type == facet_type)
    if decision.selected_action == CandidateActionType.EASIER_TASK:
        query = query.order_by(Question.difficulty.asc())
    elif decision.selected_action == CandidateActionType.HARDER_TASK:
        query = query.order_by(Question.difficulty.desc())
    else:
        query = query.order_by(Question.created_at.asc())
    candidates = query.all()

    if not candidates:
        raise NoQuestionAvailable()

    # REVIEW_TASK's whole point is repeating known content, so it never
    # needs to prefer an unattempted item; every other action prefers new
    # content when available, falling back to a repeat only if nothing else
    # exists for this skill+facet yet.
    unattempted = [q for q in candidates if q.id not in already_attempted_question_ids]
    chosen = candidates[0] if decision.selected_action == CandidateActionType.REVIEW_TASK or not unattempted else unattempted[0]

    skill = db.get(Skill, decision.skill_id)

    return ResolvedTask(
        decision_id=decision.id,
        skill_id=decision.skill_id,
        skill_name=skill.name if skill is not None else "",
        selected_action=decision.selected_action,
        assessment_type=assessment_type,
        question_id=chosen.id,
        prompt=chosen.prompt,
        difficulty=chosen.difficulty,
    )
