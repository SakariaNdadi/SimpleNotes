from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Note


def get_notes(db: Session, user_id: str, offset: int = 0, limit: int = 20, label_id: str | None = None) -> list[Note]:
    q = db.query(Note).filter(Note.user_id == user_id)
    if label_id:
        q = q.filter(Note.label_id == label_id)
    return q.order_by(Note.created_at.desc()).offset(offset).limit(limit).all()


def get_note(db: Session, note_id: str, user_id: str) -> Note | None:
    return db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()


def create_note(db: Session, user_id: str, description: str, label_id: str | None = None) -> Note:
    note = Note(user_id=user_id, description=description, label_id=label_id or None)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(db: Session, note: Note, description: str, label_id: str | None = None) -> Note:
    note.description = description
    note.label_id = label_id or None
    note.is_edited = True
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note) -> None:
    db.delete(note)
    db.commit()


def search_notes(db: Session, user_id: str, query: str) -> list[Note]:
    return (
        db.query(Note)
        .filter(Note.user_id == user_id, Note.description.ilike(f"%{query}%"))
        .order_by(Note.created_at.desc())
        .limit(50)
        .all()
    )
