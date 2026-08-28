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
    pending_retention_checkpoints: int


class StudentDashboardOut(BaseModel):
    student_user_id: str
    skills: list[SkillProgressOut]
    weak_skill_count: int
    strong_skill_count: int
    upcoming_retention_count: int
