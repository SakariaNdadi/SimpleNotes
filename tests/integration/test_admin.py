import uuid

import pytest

from app.auth.service import create_user
from app.auth.utils import create_access_token
from app.models import SiteConfig, User


@pytest.fixture
def admin_user(db):
    user = User(
        username=f"admin_{uuid.uuid4().hex[:6]}",
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="x",
        is_verified=True,
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def admin_client(client, admin_user):
    token = create_access_token(admin_user.id)
    client.cookies.set("access_token", token)
    return client, admin_user


@pytest.fixture
def extra_users(db):
    users = []
    for i in range(3):
        uid = uuid.uuid4().hex[:6]
        user = User(
            username=f"bulk_{uid}",
            email=f"bulk_{uid}@test.com",
            hashed_password="x",
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        users.append(user)
    db.flush()
    return users


# ── First-user-is-admin ───────────────────────────────────────────────────────


def test_first_user_is_admin(db):
    user = create_user(
        db, f"admin_{uuid.uuid4().hex[:6]}", f"a_{uuid.uuid4().hex}@t.com", "AdminPass1"
    )
    assert user.is_admin is True
    assert user.is_active is True


def test_second_user_is_not_admin(db):
    create_user(
        db, f"first_{uuid.uuid4().hex[:6]}", f"f_{uuid.uuid4().hex}@t.com", "AdminPass1"
    )
    second = create_user(
        db,
        f"second_{uuid.uuid4().hex[:6]}",
        f"s_{uuid.uuid4().hex}@t.com",
        "AdminPass1",
    )
    assert second.is_admin is False


def test_registration_closed_blocks_new_user(db):
    create_user(
        db, f"adm_{uuid.uuid4().hex[:6]}", f"adm_{uuid.uuid4().hex}@t.com", "AdminPass1"
    )
    db.add(SiteConfig(id=1, registration_open=False))
    db.flush()
    with pytest.raises(ValueError, match="registration_closed"):
        create_user(
            db,
            f"blocked_{uuid.uuid4().hex[:6]}",
            f"b_{uuid.uuid4().hex}@t.com",
            "AdminPass1",
        )


# ── Access control ────────────────────────────────────────────────────────────


def test_non_admin_forbidden(client, db_user):
    user, _ = db_user
    token = create_access_token(user.id)
    client.cookies.set("access_token", token)
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 403


def test_unauthenticated_forbidden(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 401


# ── Dashboard ─────────────────────────────────────────────────────────────────


def test_admin_dashboard_accessible(admin_client):
    client, _ = admin_client
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.content


# ── Users list ────────────────────────────────────────────────────────────────


def test_admin_users_list_shows_no_note_content(admin_client, db_note):
    client, _ = admin_client
    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert db_note.description.encode() not in resp.content


def test_admin_users_list_search(admin_client, db_user):
    client, _ = admin_client
    user, _ = db_user
    resp = client.get(f"/admin/users?search={user.username}")
    assert resp.status_code == 200
    assert user.username.encode() in resp.content


# ── User detail ───────────────────────────────────────────────────────────────


def test_admin_user_detail_no_note_content(admin_client, db_user, db_note):
    client, _ = admin_client
    user, _ = db_user
    resp = client.get(f"/admin/users/{user.id}")
    assert resp.status_code == 200
    assert db_note.description.encode() not in resp.content


# ── Single-user actions ───────────────────────────────────────────────────────


def test_deactivate_user(admin_client, db, db_user):
    client, _ = admin_client
    user, _ = db_user
    resp = client.post(f"/admin/users/{user.id}/deactivate", follow_redirects=False)
    assert resp.status_code == 303
    db.refresh(user)
    assert user.is_active is False


def test_activate_user(admin_client, db, db_user):
    client, _ = admin_client
    user, _ = db_user
    user.is_active = False
    db.flush()
    client.post(f"/admin/users/{user.id}/activate", follow_redirects=False)
    db.refresh(user)
    assert user.is_active is True


def test_cannot_deactivate_self(admin_client):
    client, admin = admin_client
    resp = client.post(f"/admin/users/{admin.id}/deactivate", follow_redirects=False)
    assert resp.status_code == 303
    assert "cannot_deactivate_self" in resp.headers["location"]


def test_delete_user_requires_confirm(admin_client, db, db_user):
    client, _ = admin_client
    user, _ = db_user
    resp = client.post(
        f"/admin/users/{user.id}/delete",
        data={"confirm": "wrong"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert db.query(User).filter(User.id == user.id).first() is not None


def test_delete_user_with_confirm(admin_client, db, db_user):
    client, _ = admin_client
    user, _ = db_user
    user_id = user.id
    resp = client.post(
        f"/admin/users/{user_id}/delete",
        data={"confirm": "DELETE"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert db.query(User).filter(User.id == user_id).first() is None


# ── Bulk actions ──────────────────────────────────────────────────────────────


def test_bulk_deactivate(admin_client, db, extra_users):
    client, admin = admin_client
    ids = [u.id for u in extra_users]
    resp = client.post(
        "/admin/users/bulk-action",
        data={"action": "deactivate", "user_ids": ids},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    for user in extra_users:
        db.refresh(user)
        assert user.is_active is False


def test_bulk_delete(admin_client, db, extra_users):
    client, _ = admin_client
    ids = [u.id for u in extra_users]
    resp = client.post(
        "/admin/users/bulk-action",
        data={"action": "delete", "user_ids": ids},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    for user in extra_users:
        assert db.query(User).filter(User.id == user.id).first() is None


def test_bulk_action_skips_self(admin_client, db, extra_users):
    client, admin = admin_client
    ids = [u.id for u in extra_users] + [admin.id]
    client.post(
        "/admin/users/bulk-action",
        data={"action": "deactivate", "user_ids": ids},
        follow_redirects=False,
    )
    db.refresh(admin)
    assert admin.is_active is True


def test_bulk_action_requires_selection(admin_client):
    client, _ = admin_client
    resp = client.post(
        "/admin/users/bulk-action",
        data={"action": "deactivate"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "no_selection" in resp.headers["location"]


# ── Impersonation ─────────────────────────────────────────────────────────────


def test_impersonation_sets_cookie(admin_client, db_user):
    client, _ = admin_client
    user, _ = db_user
    resp = client.post(f"/admin/users/{user.id}/impersonate", follow_redirects=False)
    assert resp.status_code == 303
    assert "impersonating_user_id" in resp.cookies


def test_stop_impersonation_clears_cookie(admin_client, db_user):
    client, _ = admin_client
    user, _ = db_user
    client.post(f"/admin/users/{user.id}/impersonate", follow_redirects=False)
    resp = client.post("/admin/impersonate/stop", follow_redirects=False)
    assert resp.status_code == 303
    assert client.cookies.get("impersonating_user_id") is None


# ── OAuth credentials ─────────────────────────────────────────────────────────


def test_oauth_credential_upsert(admin_client, db):
    client, _ = admin_client
    resp = client.post(
        "/admin/oauth/google",
        data={"client_id": "test-client-id", "client_secret": "test-secret"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from app.models import OAuthCredential

    record = (
        db.query(OAuthCredential).filter(OAuthCredential.provider == "google").first()
    )
    assert record is not None
    assert record.client_id == "test-client-id"


# ── Site settings ─────────────────────────────────────────────────────────────


def test_site_settings_toggle_registration(admin_client, db):
    client, _ = admin_client
    db.add(SiteConfig(id=1, registration_open=True))
    db.flush()
    resp = client.post("/admin/settings", data={}, follow_redirects=False)
    assert resp.status_code == 303
    db.expire_all()
    config = db.query(SiteConfig).filter(SiteConfig.id == 1).first()
    assert config.registration_open is False


# ── Deactivated user guard ────────────────────────────────────────────────────


def test_deactivated_user_cannot_access_app(client, db, db_user):
    user, _ = db_user
    user.is_active = False
    db.flush()
    token = create_access_token(user.id)
    client.cookies.set("access_token", token)
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 303, 401, 403)
