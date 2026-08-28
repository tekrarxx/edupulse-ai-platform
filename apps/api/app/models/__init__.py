"""Importing this package registers every ORM model on Base.metadata, which
Alembic autogeneration and the test schema bootstrap both rely on."""
from app.models.audit_log import AuditLog
from app.models.curriculum import Concept, Prerequisite, Skill, SkillFacet, Subject, Topic
from app.models.relationship import ParentStudentLink, TeacherStudentLink
from app.models.tenant import Tenant
from app.models.user import User, UserSession

__all__ = [
    "AuditLog",
    "Concept",
    "ParentStudentLink",
    "Prerequisite",
    "Skill",
    "SkillFacet",
    "Subject",
    "TeacherStudentLink",
    "Tenant",
    "Topic",
    "User",
    "UserSession",
]
