"""
Unit tests for app/notes/task_service.py.

ISTQB techniques: EP, BVA, State Transition, Decision Table.
Uses SQLite in-memory DB via conftest.py fixtures.
"""


from app.models import NoteTask
from app.notes.task_service import (
    confirm_task,
    dismiss_task,
    get_discovered_tasks,
    get_done_tasks,
    get_user_tasks,
    mark_task_done,
    save_tasks,
    set_task_status,
    unmark_task_done,
    update_task,
)


# ── save_tasks ────────────────────────────────────────────────────────────────


def test_save_tasks_creates_records_with_correct_source_status(db, unit_user, unit_note):
    """EP: saved tasks have specified source and status."""
    tasks = [{"title": "Task A", "description": "", "type": "task", "datetime": None}]
    result = save_tasks(db, unit_user.id, unit_note.id, tasks, source="nlp", status="discovered")
    assert len(result) == 1
    assert result[0].source == "nlp"
    assert result[0].status == "discovered"
    assert result[0].title == "Task A"


def test_save_tasks_re_run_deletes_old_same_source(db, unit_user, unit_note):
    """EP: re-running save_tasks with same source replaces previous records."""
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Old Task", "description": "", "type": "task", "datetime": None}],
               source="nlp", status="discovered")

    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "New Task", "description": "", "type": "task", "datetime": None}],
               source="nlp", status="discovered")

    tasks = db.query(NoteTask).filter(
        NoteTask.note_id == unit_note.id, NoteTask.source == "nlp"
    ).all()
    assert len(tasks) == 1
    assert tasks[0].title == "New Task"


def test_save_tasks_different_source_not_deleted(db, unit_user, unit_note):
    """EP: save_tasks only deletes tasks with matching source."""
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Manual Task", "description": "", "type": "task", "datetime": None}],
               source="manual", status="local")

    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "NLP Task", "description": "", "type": "task", "datetime": None}],
               source="nlp", status="discovered")

    manual = db.query(NoteTask).filter(
        NoteTask.note_id == unit_note.id, NoteTask.source == "manual"
    ).all()
    assert len(manual) == 1


# ── get_user_tasks ────────────────────────────────────────────────────────────


def test_get_user_tasks_excludes_discovered(db, unit_user, unit_note):
    """EP: discovered tasks excluded from default get_user_tasks."""
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Discovered", "description": "", "type": "task", "datetime": None}],
               source="nlp", status="discovered")
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Local task", "description": "", "type": "task", "datetime": None}],
               source="manual", status="local")

    results = get_user_tasks(db, unit_user.id)
    titles = [t.title for t in results]
    assert "Discovered" not in titles
    assert "Local task" in titles


def test_get_user_tasks_status_filter_local(db, unit_user, unit_note):
    """EP: status filter returns only tasks with that status."""
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Google task", "description": "", "type": "task", "datetime": None}],
               source="manual", status="google")
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Local filtered", "description": "", "type": "task", "datetime": None}],
               source="nlp", status="local")

    results = get_user_tasks(db, unit_user.id, status="local")
    titles = [t.title for t in results]
    assert "Local filtered" in titles
    assert "Google task" not in titles


# ── get_discovered_tasks ──────────────────────────────────────────────────────


def test_get_discovered_tasks_returns_only_discovered(db, unit_user, unit_note):
    """EP: only discovered-status tasks returned."""
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Disc task", "description": "", "type": "task", "datetime": None}],
               source="nlp", status="discovered")
    save_tasks(db, unit_user.id, unit_note.id,
               [{"title": "Local task x", "description": "", "type": "task", "datetime": None}],
               source="manual", status="local")

    results = get_discovered_tasks(db, unit_user.id)
    assert all(t.status == "discovered" for t in results)
    assert any(t.title == "Disc task" for t in results)


# ── confirm_task ──────────────────────────────────────────────────────────────


def test_confirm_task_discovered_becomes_local(db, unit_user, unit_note):
    """State Transition: discovered → local."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="To confirm", status="discovered", source="nlp")
    db.add(task)
    db.flush()

    confirm_task(db, task.id, unit_user.id)
    db.refresh(task)
    assert task.status == "local"


def test_confirm_task_non_discovered_status_unchanged(db, unit_user, unit_note):
    """Decision Table: non-discovered task → confirm is a no-op on status."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="Already local", status="local", source="manual")
    db.add(task)
    db.flush()

    confirm_task(db, task.id, unit_user.id)
    db.refresh(task)
    assert task.status == "local"


# ── dismiss_task ──────────────────────────────────────────────────────────────


def test_dismiss_task_deletes_task(db, unit_user, unit_note):
    """State Transition: dismiss removes the task entirely."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="To dismiss", status="discovered", source="nlp")
    db.add(task)
    db.flush()
    task_id = task.id

    dismiss_task(db, task_id, unit_user.id)
    found = db.query(NoteTask).filter(NoteTask.id == task_id).first()
    assert found is None


# ── set_task_status ───────────────────────────────────────────────────────────


def test_set_task_status_updates_field(db, unit_user, unit_note):
    """State Transition: status field updated to specified value."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="Status task", status="local", source="manual")
    db.add(task)
    db.flush()

    set_task_status(db, task.id, unit_user.id, "google")
    db.refresh(task)
    assert task.status == "google"


# ── get_done_tasks ────────────────────────────────────────────────────────────


def test_get_done_tasks_returns_only_done(db, unit_user, unit_note):
    """EP: only is_done=True tasks returned."""
    done = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="Done task", status="local", source="manual", is_done=True)
    pending = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                       title="Pending task", status="local", source="manual", is_done=False)
    db.add_all([done, pending])
    db.flush()

    results = get_done_tasks(db, unit_user.id)
    assert all(t.is_done for t in results)
    assert any(t.id == done.id for t in results)
    assert all(t.id != pending.id for t in results)


def test_get_done_tasks_limit_50(db, unit_user, unit_note):
    """BVA: at most 50 tasks returned even if more exist."""
    tasks = [
        NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                 title=f"Done {i}", status="local", source="manual", is_done=True)
        for i in range(55)
    ]
    db.add_all(tasks)
    db.flush()

    results = get_done_tasks(db, unit_user.id)
    assert len(results) <= 50


# ── update_task ───────────────────────────────────────────────────────────────


def test_update_task_discovered_promoted_to_local(db, unit_user, unit_note):
    """State Transition: updating a discovered task promotes it to local."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="Disc update", status="discovered", source="nlp")
    db.add(task)
    db.flush()

    update_task(db, task.id, unit_user.id,
                title="Updated title", description="",
                due_datetime=None, end_datetime=None,
                is_all_day=False, task_type="task")
    db.refresh(task)
    assert task.status == "local"
    assert task.title == "Updated title"


def test_update_task_title_truncated_at_500(db, unit_user, unit_note):
    """BVA: title longer than 500 chars is truncated."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="Short", status="local", source="manual")
    db.add(task)
    db.flush()

    long_title = "x" * 600
    update_task(db, task.id, unit_user.id,
                title=long_title, description="",
                due_datetime=None, end_datetime=None,
                is_all_day=False, task_type="task")
    db.refresh(task)
    assert len(task.title) == 500


def test_mark_task_done_and_unmark(db, unit_user, unit_note):
    """State Transition: done → undone via mark/unmark."""
    task = NoteTask(note_id=unit_note.id, user_id=unit_user.id,
                    title="Toggle task", status="local", source="manual")
    db.add(task)
    db.flush()

    mark_task_done(db, task.id, unit_user.id)
    db.refresh(task)
    assert task.is_done is True

    unmark_task_done(db, task.id, unit_user.id)
    db.refresh(task)
    assert task.is_done is False
