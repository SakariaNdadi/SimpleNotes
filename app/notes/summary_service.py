from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import NoteSummary


def get_summary(db: Session, note_id: str, user_id: str) -> NoteSummary | None:
    return (
        db.query(NoteSummary)
        .filter(NoteSummary.note_id == note_id, NoteSummary.user_id == user_id)
        .first()
    )


def save_summary(db: Session, note_id: str, user_id: str, content: str) -> NoteSummary:
    existing = get_summary(db, note_id, user_id)
    if existing:
        existing.content = content
        db.commit()
        db.refresh(existing)
        return existing
    summary = NoteSummary(note_id=note_id, user_id=user_id, content=content)
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def delete_summary(db: Session, note_id: str, user_id: str) -> None:
    db.query(NoteSummary).filter(
        NoteSummary.note_id == note_id, NoteSummary.user_id == user_id
    ).delete()
    db.commit()
