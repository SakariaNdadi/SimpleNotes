import uuid


def test_get_profile_page(auth_client):
    client, _ = auth_client
    r = client.get("/profile")
    assert r.status_code == 200


def test_update_username_success(auth_client, db_user):
    client, user = auth_client
    _, password = db_user
    new_name = f"upd_{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/profile",
        data={
            "username": new_name,
            "email": user.email,
            "current_password": password,
        },
    )
    assert r.status_code == 200
    assert "Profile updated" in r.text


def test_update_wrong_password(auth_client, db_user):
    client, user = auth_client
    r = client.post(
        "/profile",
        data={
            "username": user.username,
            "email": user.email,
            "current_password": "WrongPass999!",
        },
    )
    assert r.status_code == 422


def test_unauthenticated_profile(client):
    r = client.get("/profile")
    assert r.status_code == 401
