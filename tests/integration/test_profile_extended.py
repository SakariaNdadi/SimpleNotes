"""
Extended integration tests for /profile route not covered in test_profile.py.

ISTQB techniques: EP, State Transition, Error Guessing.
"""
import uuid

import pytest

from app.auth.utils import verify_password


def _profile_data(user, **overrides):
    """Return base profile form data using the user's current values."""
    data = {
        "username": user.username,
        "email": user.email,
        "current_password": "TestPass123!",
        "new_password": "",
        "confirm_password": "",
    }
    data.update(overrides)
    return data


# ── Email update ──────────────────────────────────────────────────────────────


def test_update_email_sets_is_verified_false(auth_client, db, db_user):
    """State Transition: changing email marks user as unverified."""
    client, user = auth_client
    uid = uuid.uuid4().hex[:6]
    new_email = f"new_{uid}@example.com"

    r = client.post("/profile", data=_profile_data(user, email=new_email))
    assert r.status_code == 200

    db.refresh(user)
    assert user.email == new_email
    assert user.is_verified is False


def test_update_email_already_in_use_returns_422(auth_client, db, db_user):
    """EG: email already belonging to another account → 422."""
    client, user = auth_client

    # Create a second user whose email we'll try to claim
    uid = uuid.uuid4().hex[:8]
    from app.models import User
    from app.auth.utils import hash_password
    other = User(
        username=f"other_{uid}",
        email=f"taken_{uid}@example.com",
        hashed_password=hash_password("TestPass123!"),
        is_verified=True,
    )
    db.add(other)
    db.flush()

    r = client.post("/profile", data=_profile_data(user, email=other.email))
    assert r.status_code == 422
    assert "Email already in use" in r.text


# ── Password update ───────────────────────────────────────────────────────────


def test_update_password_via_profile(auth_client, db, db_user):
    """EP: valid new_password updates hashed_password in DB."""
    client, user = auth_client
    r = client.post("/profile", data=_profile_data(
        user,
        new_password="NewSecure456!",
        confirm_password="NewSecure456!",
    ))
    assert r.status_code == 200

    db.refresh(user)
    assert verify_password("NewSecure456!", user.hashed_password) is True


def test_wrong_current_password_returns_422(auth_client, db_user):
    """EG: incorrect current_password → 422.

    The template does not render errors.current_password inline, but the router
    still returns 422 when current password verification fails.
    """
    client, user = auth_client
    r = client.post("/profile", data=_profile_data(
        user,
        current_password="WrongPass999!",
    ))
    assert r.status_code == 422


# ── Username validation ───────────────────────────────────────────────────────


def test_update_username_invalid_format_returns_422(auth_client, db_user):
    """EP: username with invalid chars → 422."""
    client, user = auth_client
    r = client.post("/profile", data=_profile_data(
        user,
        username="bad user!",
    ))
    assert r.status_code == 422
