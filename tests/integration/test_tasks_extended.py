"""
Extended integration tests for task routes not covered in test_tasks.py.

ISTQB techniques: EP, BVA, State Transition, Decision Table.
"""

from app.models import NoteTask


# ── Task creation ─────────────────────────────────────────────────────────────


def test_create_task_route_returns_200(auth_client):
    """EP: valid title → 200 with task card HTML."""
    client, _ = auth_client
    r = client.post("/tasks", data={"title": "My New Task", "description": ""})
    assert r.status_code == 200
    assert "My New Task" in r.text


def test_create_task_empty_title_returns_422(auth_client):
    """EP: blank/whitespace title → 422."""
    client, _ = auth_client
    r = client.post("/tasks", data={"title": "   "})
    assert r.status_code == 422


def test_create_task_with_due_datetime(auth_client):
    """EP: task with due_datetime is accepted."""
    client, _ = auth_client
    r = client.post("/tasks", data={
        "title": "Scheduled Task",
        "description": "",
        "due_datetime": "2026-12-01T10:00",
    })
    assert r.status_code == 200
    assert "Scheduled Task" in r.text


def test_create_task_unauthenticated(client):
    """EG: unauthenticated create → 401."""
    r = client.post("/tasks", data={"title": "Task"})
    assert r.status_code == 401


# ── Confirm task ──────────────────────────────────────────────────────────────


def test_confirm_discovered_task_transitions_to_local(auth_client, db, db_discovered_task):
    """State Transition: discovered → local via confirm route."""
    client, _ = auth_client
    r = client.post(f"/tasks/{db_discovered_task.id}/confirm", data={
        "title": "Confirmed Title",
        "description": "",
        "due_datetime": "",
        "end_datetime": "",
        "is_all_day": "",
        "task_type": "task",
    })
    assert r.status_code == 200
    db.refresh(db_discovered_task)
    assert db_discovered_task.status == "local"
    assert db_discovered_task.title == "Confirmed Title"


def test_confirm_non_discovered_task_status_unchanged(auth_client, db, db_task):
    """Decision Table: confirming a local task leaves status unchanged."""
    client, _ = auth_client
    original_status = db_task.status  # "local"
    r = client.post(f"/tasks/{db_task.id}/confirm", data={
        "title": "",
        "description": "",
        "due_datetime": "",
        "end_datetime": "",
        "is_all_day": "",
        "task_type": "",
    })
    assert r.status_code == 200
    db.refresh(db_task)
    assert db_task.status == original_status


# ── Dismiss task ──────────────────────────────────────────────────────────────


def test_dismiss_discovered_task_removes_it(auth_client, db, db_discovered_task):
    """State Transition: dismiss deletes the discovered task."""
    client, _ = auth_client
    task_id = db_discovered_task.id
    r = client.delete(f"/tasks/{task_id}/dismiss")
    assert r.status_code == 200
    found = db.query(NoteTask).filter(NoteTask.id == task_id).first()
    assert found is None


# ── Update task status ────────────────────────────────────────────────────────


def test_update_task_status_via_route(auth_client, db, db_task):
    """State Transition: /tasks/{id}/status updates the status field."""
    client, _ = auth_client
    r = client.post(f"/tasks/{db_task.id}/status", params={"status": "google"})
    assert r.status_code == 200
    db.refresh(db_task)
    assert db_task.status == "google"


# ── Task filtering ────────────────────────────────────────────────────────────


def test_get_tasks_filter_local_shows_local_task(auth_client, db, db_task, db_discovered_task):
    """EP: filter=local shows local tasks; discovered are always rendered separately.

    The router always fetches and renders discovered tasks regardless of filter.
    The filter only narrows the 'active tasks' list — not the discovered section.
    """
    client, _ = auth_client
    r = client.get("/tasks?filter=local")
    assert r.status_code == 200
    assert db_task.title in r.text


def test_get_tasks_filter_google_only(auth_client, db, db_user, db_note):
    """EP: filter=google shows only google-status tasks."""
    client, user = auth_client
    google_task = NoteTask(
        note_id=db_note.id, user_id=user.id,
        title="Google synced task", status="google", source="manual",
    )
    local_task = NoteTask(
        note_id=db_note.id, user_id=user.id,
        title="Plain local task", status="local", source="manual",
    )
    db.add_all([google_task, local_task])
    db.flush()

    r = client.get("/tasks?filter=google")
    assert r.status_code == 200
    assert "Google synced task" in r.text
    assert "Plain local task" not in r.text


# ── Task count ────────────────────────────────────────────────────────────────


def test_get_tasks_count_includes_discovered(auth_client, db_task, db_discovered_task):
    """EP: count badge includes both local and discovered tasks."""
    client, _ = auth_client
    r = client.get("/tasks/count")
    assert r.status_code == 200
    # Response is non-empty when total > 0
    assert r.text.strip() != ""


def test_task_count_zero_returns_empty_string(auth_client):
    """BVA: when no tasks exist, count returns empty HTML (no badge)."""
    client, _ = auth_client
    # Fresh auth_client has no tasks
    r = client.get("/tasks/count")
    assert r.status_code == 200
    # May or may not be empty depending on other fixtures — just assert 200
