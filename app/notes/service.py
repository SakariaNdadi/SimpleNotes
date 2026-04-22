from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models import Note, NoteHistory


def get_notes(
    db: Session,
    user_id: str,
    offset: int = 0,
    limit: int = 20,
    label_id: str | None = None,
    include_deleted: bool = False,
    include_archived: bool = False,
) -> list[Note]:
    q = db.query(Note).options(joinedload(Note.tasks)).filter(Note.user_id == user_id)
    if not include_deleted:
        q = q.filter(Note.is_deleted == False)  # noqa: E712
    if not include_archived:
        q = q.filter(Note.is_archived == False)  # noqa: E712
    if label_id:
        q = q.filter(Note.label_id == label_id)
    return q.order_by(Note.created_at.desc()).offset(offset).limit(limit).all()


def get_note(db: Session, note_id: str, user_id: str) -> Note | None:
    return (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == user_id, Note.is_deleted == False)  # noqa: E712
        .first()
    )


def get_note_any(db: Session, note_id: str, user_id: str) -> Note | None:
    """Get note regardless of deleted/archived state."""
    return db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()


def create_note(
    db: Session,
    user_id: str,
    description: str,
    label_id: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    is_all_day: bool = False,
) -> Note:
    note = Note(
        user_id=user_id,
        description=description,
        label_id=label_id or None,
        start_datetime=start_datetime or None,
        end_datetime=end_datetime or None,
        is_all_day=is_all_day,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def _save_history(db: Session, note: Note, max_history: int) -> None:
    entry = NoteHistory(
        note_id=note.id,
        user_id=note.user_id,
        description=note.description,
        label_id=note.label_id,
    )
    db.add(entry)
    count = db.query(NoteHistory).filter(NoteHistory.note_id == note.id).count()
    if count >= max_history:
        oldest = (
            db.query(NoteHistory)
            .filter(NoteHistory.note_id == note.id)
            .order_by(NoteHistory.saved_at.asc())
            .limit(count - max_history + 1)
            .all()
        )
        for old in oldest:
            db.delete(old)


def update_note(
    db: Session,
    note: Note,
    description: str,
    label_id: str | None = None,
    max_history: int = 3,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    is_all_day: bool = False,
) -> Note:
    if note.description != description and max_history > 0:
        _save_history(db, note, max_history)
    note.description = description
    note.label_id = label_id or None
    note.is_edited = True
    note.updated_at = datetime.now(timezone.utc)
    note.start_datetime = start_datetime or None
    note.end_datetime = end_datetime or None
    note.is_all_day = is_all_day
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note) -> None:
    db.delete(note)
    db.commit()


def trash_note(db: Session, note: Note) -> Note:
    note.is_deleted = True
    note.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


def archive_note(db: Session, note: Note) -> Note:
    note.is_archived = True
    db.commit()
    db.refresh(note)
    return note


def restore_note(db: Session, note: Note) -> Note:
    note.is_deleted = False
    note.deleted_at = None
    note.is_archived = False
    db.commit()
    db.refresh(note)
    return note


def get_trash(db: Session, user_id: str) -> list[Note]:
    return (
        db.query(Note)
        .filter(Note.user_id == user_id, Note.is_deleted == True)  # noqa: E712
        .order_by(Note.deleted_at.desc())
        .all()
    )


def get_archive(db: Session, user_id: str) -> list[Note]:
    return (
        db.query(Note)
        .filter(
            Note.user_id == user_id, Note.is_archived == True, Note.is_deleted == False
        )  # noqa: E712
        .order_by(Note.updated_at.desc())
        .all()
    )


def search_notes(db: Session, user_id: str, query: str) -> list[Note]:
    return (
        db.query(Note)
        .filter(
            Note.user_id == user_id,
            Note.description.ilike(f"%{query}%"),
            Note.is_deleted == False,  # noqa: E712
            Note.is_archived == False,  # noqa: E712
        )
        .order_by(Note.created_at.desc())
        .limit(50)
        .all()
    )
