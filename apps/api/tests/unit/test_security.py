from datetime import timedelta

import jwt
import pytest

from app.core import security


def test_hash_password_produces_argon2id_hash() -> None:
    hashed = security.hash_password("correct-horse-battery")
    assert hashed.startswith("$argon2id$")


def test_verify_password_accepts_correct_password() -> None:
    hashed = security.hash_password("correct-horse-battery")
    assert security.verify_password("correct-horse-battery", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = security.hash_password("correct-horse-battery")
    assert security.verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_malformed_hash_without_raising() -> None:
    assert security.verify_password("anything", "not-a-real-hash") is False


def test_access_token_round_trips() -> None:
    token, expires_at = security.create_access_token(user_id="u1", tenant_id="t1", role="STUDENT")
    payload = security.decode_access_token(token)
    assert payload["sub"] == "u1"
    assert payload["tenant_id"] == "t1"
    assert payload["role"] == "STUDENT"


def test_expired_access_token_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(security, "ACCESS_TOKEN_TTL", timedelta(seconds=-1))
    token, _ = security.create_access_token(user_id="u1", tenant_id="t1", role="STUDENT")
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(token)


def test_tampered_token_is_rejected() -> None:
    token, _ = security.create_access_token(user_id="u1", tenant_id="t1", role="STUDENT")
    # Flip a character in the middle of the signature segment rather than the
    # last character: base64url padding means some final-character swaps
    # decode to the same underlying bytes, which would make this test flaky.
    midpoint = len(token) // 2
    flipped_char = "A" if token[midpoint] != "A" else "B"
    tampered = token[:midpoint] + flipped_char + token[midpoint + 1 :]
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(tampered)


def test_refresh_token_is_stored_only_as_a_hash() -> None:
    raw_token, token_hash, _ = security.generate_refresh_token()
    assert raw_token != token_hash
    assert security.hash_refresh_token(raw_token) == token_hash


def test_two_generated_refresh_tokens_are_different() -> None:
    first, _, _ = security.generate_refresh_token()
    second, _, _ = security.generate_refresh_token()
    assert first != second
