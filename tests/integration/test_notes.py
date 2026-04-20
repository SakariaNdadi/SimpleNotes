import pytest


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
