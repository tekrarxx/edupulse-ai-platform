"""Shared column helpers.

Primary keys are stored as 36-char UUID strings rather than the Postgres
native UUID type so the same model definitions run unmodified against both
Postgres (docker compose) and SQLite (tests/conftest.py's local fallback,
§86) — the project has no native-Postgres-only column type anywhere yet, and
switching later is a single-file change confined to this module.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import mapped_column


def uuid_pk():
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


def uuid_fk(target: str, *, nullable: bool = False):
    from sqlalchemy import ForeignKey

    return mapped_column(String(36), ForeignKey(target), nullable=nullable)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
