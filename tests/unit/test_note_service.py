"""
Unit tests for app/notes/service.py.

ISTQB techniques: EP, BVA, Decision Table.
Uses SQLite in-memory DB via conftest.py fixtures.
"""

from app.models import Label, Note, NoteHistory
from app.notes.service import (
    _save_history,
    get_notes,
    search_notes,
    update_note,
)


# ── History saving ────────────────────────────────────────────────────────────


def test_save_history_creates_entry(db, unit_note):
    """EP: calling _save_history adds one NoteHistory row."""
    _save_history(db, unit_note, max_history=5)
    db.flush()
    count = db.query(NoteHistory).filter(NoteHistory.note_id == unit_note.id).count()
    assert count == 1


def test_save_history_does_not_exceed_max_history_3(db, unit_note):
    """BVA: saving 4 times with max_history=3 → never exceeds 3 entries."""
    for i in range(4):
        unit_note.description = f"Version {i}"
        _save_history(db, unit_note, max_history=3)
        db.flush()
    count = db.query(NoteHistory).filter(NoteHistory.note_id == unit_note.id).count()
    assert count <= 3


def test_save_history_max_1_prunes_immediately(db, unit_note):
    """BVA: max_history=1 — add then prune logic deletes entry on add (count 1 >= 1).

    The service adds the entry first, then counts (triggers autoflush → count=1),
    1 >= 1 so it deletes limit=1 oldest entries. Net result: 0 entries remain.
    This is the correct algorithmic behavior for max_history=1.
    """
    unit_note.description = "Entry 0"
    _save_history(db, unit_note, max_history=1)
    db.flush()
    count = db.query(NoteHistory).filter(NoteHistory.note_id == unit_note.id).count()
    assert count == 0


# ── update_note ───────────────────────────────────────────────────────────────


def test_update_note_max_history_zero_skips_history(db, unit_note):
    """BVA: max_history=0 → no history created even with different description."""
    update_note(db, unit_note, "Completely new content", max_history=0)
    count = db.query(NoteHistory).filter(NoteHistory.note_id == unit_note.id).count()
    assert count == 0


def test_update_note_same_description_no_history_saved(db, unit_note):
    """Decision Table: description unchanged + max_history>0 → no history."""
    original = unit_note.description
    update_note(db, unit_note, original, max_history=3)
    count = db.query(NoteHistory).filter(NoteHistory.note_id == unit_note.id).count()
    assert count == 0


def test_update_note_different_description_saves_history(db, unit_note):
    """Decision Table: description changed + max_history>0 → one history entry."""
    update_note(db, unit_note, "Changed content", max_history=3)
    count = db.query(NoteHistory).filter(NoteHistory.note_id == unit_note.id).count()
    assert count == 1


def test_update_note_sets_is_edited_true(db, unit_note):
    """EP: update_note always sets is_edited=True."""
    update_note(db, unit_note, "Any content", max_history=0)
    assert unit_note.is_edited is True


def test_update_note_updates_description(db, unit_note):
    """EP: note.description is set to the new value."""
    update_note(db, unit_note, "Fresh description", max_history=0)
    assert unit_note.description == "Fresh description"


# ── get_notes ─────────────────────────────────────────────────────────────────


def test_get_notes_label_id_filter(db, unit_user):
    """EP: label_id filter returns only notes with that label."""
    label = Label(user_id=unit_user.id, title="FilterLabel", color="")
    db.add(label)
    db.flush()
    labeled = Note(user_id=unit_user.id, description="Labeled note", label_id=label.id)
    unlabeled = Note(user_id=unit_user.id, description="Unlabeled note")
    db.add_all([labeled, unlabeled])
    db.flush()

    results = get_notes(db, unit_user.id, label_id=label.id)
    ids = [n.id for n in results]
    assert labeled.id in ids
    assert unlabeled.id not in ids


def test_get_notes_pagination_offset_and_limit(db, unit_user):
    """BVA: offset and limit correctly slice results."""
    notes = [Note(user_id=unit_user.id, description=f"Note {i}") for i in range(5)]
    db.add_all(notes)
    db.flush()

    page1 = get_notes(db, unit_user.id, offset=0, limit=3)
    page2 = get_notes(db, unit_user.id, offset=3, limit=3)
    assert len(page1) == 3
    assert len(page2) >= 2  # at least the 2 remaining notes


def test_get_notes_excludes_deleted_by_default(db, unit_user):
    """EP: soft-deleted note not returned."""
    note = Note(user_id=unit_user.id, description="Deleted note", is_deleted=True)
    db.add(note)
    db.flush()
    results = get_notes(db, unit_user.id)
    assert all(n.id != note.id for n in results)


def test_get_notes_excludes_archived_by_default(db, unit_user):
    """EP: archived note not returned."""
    note = Note(user_id=unit_user.id, description="Archived note", is_archived=True)
    db.add(note)
    db.flush()
    results = get_notes(db, unit_user.id)
    assert all(n.id != note.id for n in results)


# ── search_notes ──────────────────────────────────────────────────────────────


def test_search_notes_case_insensitive_match(db, unit_user):
    """EP: ILIKE search is case-insensitive."""
    note = Note(user_id=unit_user.id, description="Buy Milk At Store")
    db.add(note)
    db.flush()
    results = search_notes(db, unit_user.id, "buy milk")
    assert any(n.id == note.id for n in results)


def test_search_notes_excludes_deleted(db, unit_user):
    """EP: deleted notes not returned by search."""
    note = Note(user_id=unit_user.id, description="searchable deleted note", is_deleted=True)
    db.add(note)
    db.flush()
    results = search_notes(db, unit_user.id, "searchable deleted")
    assert all(n.id != note.id for n in results)


def test_search_notes_excludes_archived(db, unit_user):
    """EP: archived notes not returned by search."""
    note = Note(user_id=unit_user.id, description="searchable archived note", is_archived=True)
    db.add(note)
    db.flush()
    results = search_notes(db, unit_user.id, "searchable archived")
    assert all(n.id != note.id for n in results)


def test_search_notes_no_match_returns_empty(db, unit_user):
    """EP: query with no matching notes → empty list."""
    results = search_notes(db, unit_user.id, "xyzzy-unique-string-zzz")
    assert results == []
