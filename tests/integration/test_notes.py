def test_create_note(auth_client):
    client, _ = auth_client
    r = client.post("/notes", data={"description": "Hello integration test"})
    assert r.status_code == 200
    assert "Hello integration test" in r.text


def test_create_note_empty(auth_client):
    client, _ = auth_client
    r = client.post("/notes", data={"description": "   "})
    assert r.status_code == 422


def test_list_notes(auth_client):
    client, _ = auth_client
    r = client.get("/notes")
    assert r.status_code == 200


def test_get_note(auth_client, db_note):
    client, _ = auth_client
    r = client.get(f"/notes/{db_note.id}")
    assert r.status_code == 200
    assert db_note.description in r.text


def test_get_note_not_found(auth_client):
    client, _ = auth_client
    r = client.get("/notes/nonexistent-id")
    assert r.status_code == 404


def test_get_note_edit_form(auth_client, db_note):
    client, _ = auth_client
    r = client.get(f"/notes/{db_note.id}/edit")
    assert r.status_code == 200
    assert db_note.description in r.text


def test_update_note(auth_client, db_note):
    client, _ = auth_client
    r = client.put(f"/notes/{db_note.id}", data={"description": "Updated content"})
    assert r.status_code == 200
    assert "Updated content" in r.text


def test_update_note_empty(auth_client, db_note):
    client, _ = auth_client
    r = client.put(f"/notes/{db_note.id}", data={"description": "  "})
    assert r.status_code == 422


def test_get_note_history(auth_client, db_note):
    client, _ = auth_client
    r = client.get(f"/notes/{db_note.id}/history")
    assert r.status_code == 200


def test_delete_note(auth_client, db_note):
    client, _ = auth_client
    r = client.delete(f"/notes/{db_note.id}")
    assert r.status_code == 200


def test_trash_feed(auth_client):
    client, _ = auth_client
    r = client.get("/notes/trash")
    assert r.status_code == 200


def test_archive_note(auth_client, db_note):
    client, _ = auth_client
    r = client.post(f"/notes/{db_note.id}/archive")
    assert r.status_code == 200


def test_archive_feed(auth_client):
    client, _ = auth_client
    r = client.get("/notes/archive")
    assert r.status_code == 200


def test_restore_note(auth_client, db_note):
    client, _ = auth_client
    client.post(f"/notes/{db_note.id}/archive")
    r = client.post(f"/notes/{db_note.id}/restore")
    assert r.status_code == 200


def test_permanent_delete(auth_client, db_note):
    client, _ = auth_client
    r = client.delete(f"/notes/{db_note.id}/permanent")
    assert r.status_code == 200


def test_search_notes(auth_client):
    client, _ = auth_client
    r = client.post("/notes/search", data={"query": "test"})
    assert r.status_code == 200


def test_unauthenticated_notes_list(client):
    r = client.get("/notes")
    assert r.status_code == 401


# ── Saved summary pre-population ─────────────────────────────────────────────


def test_note_card_shows_saved_summary(auth_client, db, db_note, db_user):
    """EP: GET /notes/{id} with a saved summary → summary content rendered inline."""
    from app.notes.summary_service import save_summary

    user, _ = db_user
    save_summary(db, db_note.id, user.id, "Pre-saved summary text")

    client, _ = auth_client
    r = client.get(f"/notes/{db_note.id}")
    assert r.status_code == 200
    assert "Pre-saved summary text" in r.text


def test_note_list_shows_saved_summary(auth_client, db, db_note, db_user):
    """EP: GET /notes with a note that has a saved summary → summary content rendered inline."""
    from app.notes.summary_service import save_summary

    user, _ = db_user
    save_summary(db, db_note.id, user.id, "Listed note summary")

    client, _ = auth_client
    r = client.get("/notes")
    assert r.status_code == 200
    assert "Listed note summary" in r.text


def test_note_card_no_summary_div_empty(auth_client, db_note):
    """EP: GET /notes/{id} with no saved summary → summary container empty."""
    client, _ = auth_client
    r = client.get(f"/notes/{db_note.id}")
    assert r.status_code == 200
    assert f'id="summary-{db_note.id}"></div>' in r.text


def test_update_note_invalidates_saved_summary(auth_client, db, db_note, db_user):
    """EP: PUT /notes/{id} deletes any saved summary so next request regenerates."""
    from app.notes.summary_service import save_summary
    from app.models import NoteSummary

    user, _ = db_user
    save_summary(db, db_note.id, user.id, "Stale summary")

    client, _ = auth_client
    r = client.put(f"/notes/{db_note.id}", data={"description": "Edited note content"})
    assert r.status_code == 200

    remaining = (
        db.query(NoteSummary)
        .filter(NoteSummary.note_id == db_note.id, NoteSummary.user_id == user.id)
        .first()
    )
    assert remaining is None


def test_update_note_without_summary_does_not_error(auth_client, db_note):
    """EG: PUT /notes/{id} when no summary exists → update succeeds normally."""
    client, _ = auth_client
    r = client.put(f"/notes/{db_note.id}", data={"description": "Clean edit"})
    assert r.status_code == 200
    assert "Clean edit" in r.text
