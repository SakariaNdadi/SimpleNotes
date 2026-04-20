import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.utils import generate_secure_token, hash_token
from app.models import EmailVerificationToken, PasswordResetToken


def _reg_data(uid=None):
    uid = uid or uuid.uuid4().hex[:8]
    return {
        "username": f"tuser_{uid}",
        "email": f"tuser_{uid}@example.com",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
    }


def test_register_success(client):
    r = client.post("/register", data=_reg_data())
    assert r.status_code == 200
    assert "Account created" in r.text


def test_register_duplicate_username(client, db_user):
    user, _ = db_user
    data = _reg_data()
    data["username"] = user.username
    r = client.post("/register", data=data)
    assert r.status_code == 422
    assert "Username already taken" in r.text


def test_register_password_mismatch(client):
    data = _reg_data()
    data["confirm_password"] = "Different1!"
    r = client.post("/register", data=data)
    assert r.status_code == 422
    assert "Passwords do not match" in r.text


def test_login_success(client, db_user):
    user, password = db_user
    r = client.post("/login", data={"username": user.username, "password": password})
    assert r.status_code == 200
    assert "access_token" in client.cookies


def test_login_bad_credentials(client):
    r = client.post("/login", data={"username": "nobody", "password": "WrongPass1!"})
    assert r.status_code == 401
    assert "Invalid username or password" in r.text


def test_logout(auth_client):
    client, _ = auth_client
    r = client.post("/logout")
    assert r.status_code == 200


def test_verify_email_invalid_token(client):
    r = client.get("/verify-email/invalidtoken")
    assert r.status_code == 200
    assert "Invalid or expired" in r.text


def test_verify_email_valid_token(client, db, db_user):
    user, _ = db_user
    raw, hashed = generate_secure_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.add(EmailVerificationToken(user_id=user.id, token_hash=hashed, expires_at=expires))
    db.flush()
    r = client.get(f"/verify-email/{raw}")
    assert r.status_code == 200
    assert "verified" in r.text.lower()


def test_forgot_password_shows_success(client):
    r = client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert "reset link" in r.text.lower()


def test_reset_password_invalid_token(client):
    r = client.get("/reset-password/badtoken")
    assert r.status_code == 200
    assert "Invalid or expired" in r.text


def test_reset_password_success(client, db, db_user):
    user, _ = db_user
    raw, hashed = generate_secure_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    record = PasswordResetToken(user_id=user.id, token_hash=hashed, expires_at=expires, used=False)
    db.add(record)
    db.flush()
    r = client.post(
        f"/reset-password/{raw}",
        data={"password": "NewPass456!", "confirm_password": "NewPass456!"},
    )
    assert r.status_code == 200
    assert "Password reset" in r.text
