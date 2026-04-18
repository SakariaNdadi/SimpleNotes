from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import NoteTask


def save_tasks(db: Session, user_id: str, note_id: str, tasks: list[dict]) -> list[NoteTask]:
    db.query(NoteTask).filter(NoteTask.note_id == note_id).delete()
    saved = []
    for t in tasks:
        task = NoteTask(
            note_id=note_id,
            user_id=user_id,
            title=t.get("title", "")[:500],
            description=t.get("description", ""),
            task_type=t.get("type", "task"),
            due_datetime=t.get("datetime"),
        )
        db.add(task)
        saved.append(task)
    db.commit()
    return saved


def get_user_tasks(db: Session, user_id: str, done: bool = False) -> list[NoteTask]:
    return (
        db.query(NoteTask)
        .filter(NoteTask.user_id == user_id, NoteTask.is_done == done)
        .order_by(NoteTask.created_at.desc())
        .all()
    )


def mark_task_done(db: Session, task_id: str, user_id: str) -> NoteTask | None:
    task = db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).first()
    if task:
        task.is_done = True
        db.commit()
    return task
