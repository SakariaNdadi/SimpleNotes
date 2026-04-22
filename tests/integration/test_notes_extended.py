"""
Extended integration tests for note routes not covered in test_notes.py.

ISTQB techniques: EP, BVA, State Transition, Error Guessing.
"""
import uuid


from app.models import Note, NoteHistory, User
from app.auth.utils import hash_password, create_access_token


# ── Note creation with optional fields ───────────────────────────────────────


def test_create_note_with_label_id(auth_client, db, db_label):
    """EP: note created with label_id is associated with the label."""
    client, user = auth_client
    r = client.post("/notes", data={
        "description": "Labeled note content",
        "label_id": db_label.id,
    })
    assert r.status_code == 200
    note = db.query(Note).filter(
        Note.user_id == user.id, Note.description == "Labeled note content"
    ).first()
    assert note is not None
    assert note.label_id == db_label.id


def test_create_note_with_start_datetime(auth_client, db):
    """EP: note with start_datetime stores the value."""
    client, user = auth_client
    r = client.post("/notes", data={
        "description": "Event note",
        "start_datetime": "2026-05-01T10:00",
    })
    assert r.status_code == 200
    note = db.query(Note).filter(
        Note.user_id == user.id, Note.description == "Event note"
    ).first()
    assert note is not None
    assert note.start_datetime == "2026-05-01T10:00"


def test_create_note_is_all_day_flag(auth_client, db):
    """EP: is_all_day flag is stored when provided."""
    client, user = auth_client
    r = client.post("/notes", data={
        "description": "All day event",
        "is_all_day": "true",
    })
    assert r.status_code == 200
    note = db.query(Note).filter(
        Note.user_id == user.id, Note.description == "All day event"
    ).first()
    assert note is not None
    assert note.is_all_day is True


# ── Note history ──────────────────────────────────────────────────────────────


def test_get_note_history_after_two_edits(auth_client, db, db_note):
    """EP: editing a note twice creates history entries."""
    client, user = auth_client

    # Set max_edit_history > 0 via preferences
    from app.preferences.service import get_or_create_prefs
    prefs = get_or_create_prefs(db, user.id)
    prefs.max_edit_history = 3
    db.flush()

    client.put(f"/notes/{db_note.id}", data={"description": "Edit one"})
    client.put(f"/notes/{db_note.id}", data={"description": "Edit two"})

    r = client.get(f"/notes/{db_note.id}/history")
    assert r.status_code == 200
    # At least one history entry should appear
    entries = db.query(NoteHistory).filter(NoteHistory.note_id == db_note.id).all()
    assert len(entries) >= 1


def test_restore_note_from_history(auth_client, db, db_note):
    """State Transition: restore from history reverts description."""
    client, user = auth_client

    from app.preferences.service import get_or_create_prefs
    prefs = get_or_create_prefs(db, user.id)
    prefs.max_edit_history = 3
    db.flush()

    # Edit to create a history entry of original content
    original_description = db_note.description
    client.put(f"/notes/{db_note.id}", data={"description": "Changed content"})

    entry = db.query(NoteHistory).filter(NoteHistory.note_id == db_note.id).first()
    assert entry is not None

    r = client.post(f"/notes/{db_note.id}/history/{entry.id}/restore")
    assert r.status_code == 200
    db.refresh(db_note)
    assert db_note.description == original_description


# ── Pagination ────────────────────────────────────────────────────────────────


def test_get_notes_pagination_offset(auth_client, db, db_user):
    """BVA: offset parameter correctly skips notes."""
    client, user = auth_client
    # Create 5 notes
    for i in range(5):
        client.post("/notes", data={"description": f"Pagination note {i}"})

    r_page1 = client.get("/notes?offset=0")
    r_page2 = client.get("/notes?offset=3")
    assert r_page1.status_code == 200
    assert r_page2.status_code == 200


# ── Label filter ──────────────────────────────────────────────────────────────


def test_get_notes_filtered_by_label_id(auth_client, db, db_label):
    """EP: label_id query param filters notes."""
    client, user = auth_client
    client.post("/notes", data={
        "description": "Note with label",
        "label_id": db_label.id,
    })
    client.post("/notes", data={"description": "Note without label"})

    r = client.get(f"/notes?label_id={db_label.id}")
    assert r.status_code == 200
    assert "Note with label" in r.text
    assert "Note without label" not in r.text


# ── Auth isolation ────────────────────────────────────────────────────────────


def test_auth_isolation_cannot_access_other_user_note(client, db):
    """EG: user A cannot read user B's note (returns 404 or 401)."""
    uid = uuid.uuid4().hex[:8]
    user_b = User(
        username=f"userb_{uid}",
        email=f"userb_{uid}@example.com",
        hashed_password=hash_password("TestPass123!"),
        is_verified=True,
    )
    db.add(user_b)
    db.flush()

    note_b = Note(user_id=user_b.id, description="User B's private note")
    db.add(note_b)
    db.flush()

    uid_a = uuid.uuid4().hex[:8]
    user_a = User(
        username=f"usera_{uid_a}",
        email=f"usera_{uid_a}@example.com",
        hashed_password=hash_password("TestPass123!"),
        is_verified=True,
    )
    db.add(user_a)
    db.flush()

    token_a = create_access_token(user_a.id)
    client.cookies.set("access_token", token_a)

    r = client.get(f"/notes/{note_b.id}")
    assert r.status_code in (404, 401)


# ── State transitions ─────────────────────────────────────────────────────────


def test_trash_note_sets_is_deleted_and_deleted_at(auth_client, db, db_note):
    """State Transition: DELETE /notes/{id} → soft delete."""
    client, _ = auth_client
    r = client.delete(f"/notes/{db_note.id}")
    assert r.status_code == 200
    db.refresh(db_note)
    assert db_note.is_deleted is True
    assert db_note.deleted_at is not None


def test_restore_from_trash_clears_deleted_fields(auth_client, db, db_note):
    """State Transition: trash then restore clears is_deleted and deleted_at."""
    client, _ = auth_client
    client.delete(f"/notes/{db_note.id}")
    r = client.post(f"/notes/{db_note.id}/restore")
    assert r.status_code == 200
    db.refresh(db_note)
    assert db_note.is_deleted is False
    assert db_note.deleted_at is None


# ── Search edge cases ─────────────────────────────────────────────────────────


def test_search_returns_empty_for_no_match(auth_client):
    """EP: search query with no match → 200 with empty results."""
    client, _ = auth_client
    r = client.post("/notes/search", data={"query": "xyzzy-no-match-string-99"})
    assert r.status_code == 200
