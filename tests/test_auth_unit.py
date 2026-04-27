"""Unit tests for app.services.auth helpers (no HTTP, no DB)."""

import pytest

from app.services.auth import (
    create_access_token,
    hash_password,
    user_owns_record,
    verify_password,
    _decode_token,
)


# -------------------------------------------------------
# Password hashing
# -------------------------------------------------------

def test_hash_password_returns_different_string():
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert isinstance(hashed, str)
    assert len(hashed) > 20


def test_hash_password_is_non_deterministic():
    h1 = hash_password("samepassword")
    h2 = hash_password("samepassword")
    assert h1 != h2


def test_verify_password_correct():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


# -------------------------------------------------------
# JWT tokens
# -------------------------------------------------------

def test_create_access_token_round_trip():
    token = create_access_token("user-123", "admin")
    payload = _decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_decode_invalid_token_returns_none():
    assert _decode_token("not.a.real.token") is None


def test_decode_garbage_returns_none():
    assert _decode_token("definitely-not-a-jwt") is None


# -------------------------------------------------------
# user_owns_record matrix
# -------------------------------------------------------

class _FakeUser:
    def __init__(self, user_id: str):
        self.user_id = user_id


def test_user_owns_record_anon_owns_unowned():
    assert user_owns_record(None, None) is True


def test_user_owns_record_anon_does_not_own_owned():
    assert user_owns_record(None, "user-1") is False


def test_user_owns_record_authed_owns_match():
    assert user_owns_record(_FakeUser("user-1"), "user-1") is True


def test_user_owns_record_authed_does_not_own_other():
    assert user_owns_record(_FakeUser("user-1"), "user-2") is False


def test_user_owns_record_authed_does_not_own_unowned():
    assert user_owns_record(_FakeUser("user-1"), None) is False
