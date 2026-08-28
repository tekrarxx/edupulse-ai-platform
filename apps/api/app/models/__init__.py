"""Importing this package registers every ORM model on Base.metadata, which
Alembic autogeneration and the test schema bootstrap both rely on."""
from app.models.assessment import Attempt, Question
from app.models.audit_log import AuditLog
from app.models.curriculum import Concept, Prerequisite, Skill, SkillFacet, Subject, Topic
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.knowledge_state import KnowledgeState
from app.models.observation import Observation
from app.models.relationship import ParentStudentLink, TeacherStudentLink
from app.models.retention import Hypothesis, RetentionCheckpoint
from app.models.tenant import Tenant
from app.models.user import User, UserSession

__all__ = [
    "Attempt",
    "AuditLog",
    "Concept",
    "Decision",
    "Evidence",
    "Hypothesis",
    "KnowledgeState",
    "Observation",
    "ParentStudentLink",
    "Prerequisite",
    "Question",
    "RetentionCheckpoint",
    "Skill",
    "SkillFacet",
    "Subject",
    "TeacherStudentLink",
    "Tenant",
    "Topic",
    "User",
    "UserSession",
]
