"""Unit tests for the password-reset flow (auth_service + email_service),
entirely against a monkeypatched email sender — never a live SMTP call
(§86, matches tests/unit/test_ai_gateway.py's FakeProvider convention)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.tenant import Tenant, TenantType
from app.models.user import PasswordResetToken, Role, User
from app.services import auth_service, email_service


def _make_user(db: Session) -> User:
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"resettest-{uuid.uuid4().hex}@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        display_name="Reset Test",
        role=Role.STUDENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _capture_sent_emails(monkeypatch) -> list[dict]:
    sent: list[dict] = []

    def _fake_send(*, to_email: str, reset_link: str) -> None:
        sent.append({"to_email": to_email, "reset_link": reset_link})

    monkeypatch.setattr(email_service, "send_password_reset_email", _fake_send)
    return sent


def test_request_password_reset_sends_email_for_real_user(db: Session, monkeypatch) -> None:
    user = _make_user(db)
    sent = _capture_sent_emails(monkeypatch)

    auth_service.request_password_reset(db, user.email)

    assert len(sent) == 1
    assert sent[0]["to_email"] == user.email
    assert "token=" in sent[0]["reset_link"]

    token = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).one()
    assert token.used_at is None
    assert token.expires_at > datetime.now(timezone.utc)


def test_request_password_reset_is_silent_for_unknown_email(db: Session, monkeypatch) -> None:
    """§90: no exception, no email sent, no token created — the caller
    cannot distinguish this from the "real user" case by behavior alone."""
    sent = _capture_sent_emails(monkeypatch)
    tokens_before = db.query(PasswordResetToken).count()

    auth_service.request_password_reset(db, f"never-registered-{uuid.uuid4().hex}@example.com")

    assert sent == []
    assert db.query(PasswordResetToken).count() == tokens_before


def test_reset_password_changes_password_and_marks_token_used(db: Session, monkeypatch) -> None:
    user = _make_user(db)
    sent = _capture_sent_emails(monkeypatch)
    auth_service.request_password_reset(db, user.email)
    raw_token = sent[0]["reset_link"].split("token=")[1]

    updated_user = auth_service.reset_password(db, raw_token, "brand-new-password-123")

    assert updated_user.id == user.id
    db.refresh(updated_user)
    assert verify_password("brand-new-password-123", updated_user.password_hash)

    token = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).one()
    assert token.used_at is not None


def test_reset_password_rejects_reused_token(db: Session, monkeypatch) -> None:
    user = _make_user(db)
    sent = _capture_sent_emails(monkeypatch)
    auth_service.request_password_reset(db, user.email)
    raw_token = sent[0]["reset_link"].split("token=")[1]

    auth_service.reset_password(db, raw_token, "first-new-password-1")

    with pytest.raises(auth_service.PasswordResetTokenInvalid):
        auth_service.reset_password(db, raw_token, "second-new-password-2")


def test_reset_password_rejects_expired_token(db: Session, monkeypatch) -> None:
    user = _make_user(db)
    sent = _capture_sent_emails(monkeypatch)
    auth_service.request_password_reset(db, user.email)
    raw_token = sent[0]["reset_link"].split("token=")[1]

    token = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    with pytest.raises(auth_service.PasswordResetTokenInvalid):
        auth_service.reset_password(db, raw_token, "irrelevant-new-password")


def test_reset_password_rejects_garbage_token(db: Session) -> None:
    with pytest.raises(auth_service.PasswordResetTokenInvalid):
        auth_service.reset_password(db, "not-a-real-token", "irrelevant-new-password")
