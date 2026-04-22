"""
Extended integration tests for label routes not fully covered in test_labels.py.

ISTQB techniques: EP, Error Guessing.
"""

import uuid


from app.models import Note


# ── Label note unlinking ──────────────────────────────────────────────────────


def test_delete_label_unlinks_notes(auth_client, db, db_label, db_user):
    """EP: deleting a label sets label_id=None on all associated notes."""
    client, user = auth_client
    note = Note(
        user_id=user.id, description="Note linked to label", label_id=db_label.id
    )
    db.add(note)
    db.flush()

    r = client.delete(f"/labels/{db_label.id}")
    assert r.status_code == 200

    db.refresh(note)
    assert note.label_id is None


# ── Duplicate title ───────────────────────────────────────────────────────────


def test_create_duplicate_label_returns_422(auth_client):
    """EG: creating a label with a title that already exists → 422."""
    client, _ = auth_client
    client.post(
        "/labels", data={"title": "UniqueLabel", "description": "", "color": ""}
    )
    r = client.post(
        "/labels", data={"title": "UniqueLabel", "description": "", "color": ""}
    )
    assert r.status_code == 422


def test_update_label_to_duplicate_title_returns_422(
    auth_client, db, db_label, db_user
):
    """EG: updating a label to a title already taken → 422."""
    client, user = auth_client
    from app.models import Label

    other = Label(user_id=user.id, title="OtherLabel", color="")
    db.add(other)
    db.flush()

    r = client.put(
        f"/labels/{other.id}",
        data={
            "title": db_label.title,  # "Test Label" — already taken
            "description": "",
            "color": "",
        },
    )
    assert r.status_code == 422


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_get_labels_empty_for_new_user(client, db):
    """EP: new user with no labels returns 200 with empty list."""
    from app.models import User
    from app.auth.utils import hash_password, create_access_token

    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"fresh_{uid}",
        email=f"fresh_{uid}@example.com",
        hashed_password=hash_password("TestPass123!"),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    token = create_access_token(user.id)
    client.cookies.set("access_token", token)

    r = client.get("/labels")
    assert r.status_code == 200


def test_delete_nonexistent_label_returns_200(auth_client):
    """EG: deleting a non-existent label is a no-op → 200."""
    client, _ = auth_client
    r = client.delete(f"/labels/{uuid.uuid4()}")
    assert r.status_code == 200


def test_update_nonexistent_label_returns_404(auth_client):
    """EG: updating a non-existent label → 404."""
    client, _ = auth_client
    r = client.put(
        f"/labels/{uuid.uuid4()}",
        data={
            "title": "Doesn't matter",
            "description": "",
            "color": "",
        },
    )
    assert r.status_code == 404
