"""
Unit tests for app/auth/utils.py.

ISTQB techniques: Equivalence Partitioning (EP), Boundary Value Analysis (BVA),
Error Guessing (EG).
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32-chars-ok!")
os.environ.setdefault("FERNET_KEY", "")

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.auth.utils import (
    _get_fernet,
    create_access_token,
    decode_access_token,
    decrypt_value,
    encrypt_value,
    generate_secure_token,
    hash_password,
    hash_token,
    validate_password,
    validate_username,
    verify_password,
)
from app.config import get_settings


# ── Password hashing ─────────────────────────────────────────────────────────


def test_hash_and_verify_roundtrip():
    """EP: valid password class — hash then verify returns True."""
    hashed = hash_password("MyPass1!")
    assert verify_password("MyPass1!", hashed) is True


def test_verify_wrong_password_returns_false():
    """EG: wrong credential."""
    hashed = hash_password("Correct1!")
    assert verify_password("Wrong999!", hashed) is False


# ── Username validation ───────────────────────────────────────────────────────


def test_validate_username_valid():
    """EP: valid partition."""
    assert validate_username("valid_user") is None


def test_validate_username_too_short():
    """BVA: 2 chars (below min of 3)."""
    assert validate_username("ab") is not None


def test_validate_username_boundary_min_valid():
    """BVA: exactly 3 chars — on the boundary, valid."""
    assert validate_username("abc") is None


def test_validate_username_boundary_max_valid():
    """BVA: exactly 20 chars — on the boundary, valid."""
    assert validate_username("a" * 20) is None


def test_validate_username_too_long():
    """BVA: 21 chars (above max of 20)."""
    assert validate_username("a" * 21) is not None


def test_validate_username_invalid_chars():
    """EP: invalid char class (@ not allowed)."""
    assert validate_username("user@name") is not None


def test_validate_username_with_numbers_and_underscore():
    """EP: valid chars — numbers and underscore."""
    assert validate_username("user_123") is None


# ── Password validation ───────────────────────────────────────────────────────


def test_validate_password_valid():
    """EP: valid password."""
    assert validate_password("SecurePass1") is None


def test_validate_password_boundary_8_chars():
    """BVA: exactly 8 chars with required complexity."""
    assert validate_password("Passw0rd") is None


def test_validate_password_too_short():
    """BVA: 7 chars (below min of 8)."""
    assert validate_password("Short1!") is not None


def test_validate_password_no_uppercase():
    """EP: missing uppercase."""
    assert validate_password("nouppercase1") is not None


def test_validate_password_no_digit():
    """EP: missing digit."""
    assert validate_password("NoDigitPass") is not None


# ── JWT token ─────────────────────────────────────────────────────────────────


def test_create_and_decode_token_roundtrip():
    """EP: encode user ID, decode returns same ID."""
    token = create_access_token("user-abc-123")
    assert decode_access_token(token) == "user-abc-123"


def test_decode_invalid_token_returns_none():
    """EG: malformed JWT string."""
    assert decode_access_token("not.a.valid.token") is None


def test_decode_expired_token_returns_none():
    """EG: expired token — exp in the past."""
    settings = get_settings()
    expired_payload = {
        "sub": "user-xyz",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
    assert decode_access_token(expired_token) is None


# ── Secure token generation ───────────────────────────────────────────────────


def test_generate_secure_token_raw_hash_differ():
    """EP: raw token and its hash are distinct."""
    raw, hashed = generate_secure_token()
    assert raw != hashed


def test_generate_secure_token_hash_reproducible():
    """EP: hashing raw produces the stored hash."""
    raw, hashed = generate_secure_token()
    assert hash_token(raw) == hashed


def test_hash_token_consistency():
    """EP: same input always produces same hash."""
    assert hash_token("deterministic-input") == hash_token("deterministic-input")


# ── Fernet encryption ─────────────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip():
    """EP: encrypt then decrypt returns original value."""
    enc = encrypt_value("super-secret-value")
    assert decrypt_value(enc) == "super-secret-value"


def test_decrypt_invalid_ciphertext_returns_empty():
    """EG: invalid/corrupted ciphertext returns empty string, not exception."""
    assert decrypt_value("not-valid-fernet-data") == ""


def test_get_fernet_caching_same_object():
    """EP: lru_cache(maxsize=1) returns the same Fernet instance."""
    f1 = _get_fernet()
    f2 = _get_fernet()
    assert f1 is f2
