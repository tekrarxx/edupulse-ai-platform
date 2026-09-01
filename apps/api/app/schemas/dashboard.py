from pydantic import BaseModel


class SkillProgressOut(BaseModel):
    """§26/§75 enforcement point: no mastery_probability field exists here —
    only the plain-language label. The student UI must never render a raw
    posterior float."""

    skill_id: str
    skill_name: str
    mastery_label: str
    is_weak: bool
    is_strong: bool
    next_action_label: str | None
    next_action_decision_id: str | None
    pending_retention_checkpoints: int


class StudentDashboardOut(BaseModel):
    student_user_id: str
    skills: list[SkillProgressOut]
    weak_skill_count: int
    strong_skill_count: int
    upcoming_retention_count: int


class StudentSummaryOut(BaseModel):
    """§76. Every field here traces to a real signal (weak knowledge state,
    a NOT_SUPPORTED retention verdict, an escalated Decision, a teacher-
    classified misconception) — never a fabricated heuristic."""

    student_user_id: str
    student_name: str
    needs_attention: bool
    attention_reasons: list[str]
    weak_skill_names: list[str]
    improving_skill_names: list[str]
    forgetting_skill_names: list[str]
    misconception_skill_names: list[str]
    next_action_label: str | None


class TeacherDashboardOut(BaseModel):
    students: list[StudentSummaryOut]
    students_needing_attention_count: int


class AdminDashboardOut(BaseModel):
    """§77. Tenant-wide counts only — no per-student names (§80). Plan/
    entitlement fields (ADR-016) are the narrow §59-§61 slice that exists;
    still no invoice/payment field — that remains genuinely unbuilt, not
    faked (§105)."""

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
    ai_explanations_monthly_limit: int | None
    tenant_user_count: int
    tenant_user_limit: int | None
