from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Domain models (Phase 2+) inherit from this;
    Alembic's env.py points at Base.metadata for autogeneration."""
