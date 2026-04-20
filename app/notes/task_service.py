from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import NoteTask


def create_task(
    db: Session,
    user_id: str,
    title: str,
    description: str = "",
    task_type: str = "task",
    due_datetime: str | None = None,
    end_datetime: str | None = None,
    is_all_day: bool = False,
) -> NoteTask:
    task = NoteTask(
        note_id=None,
        user_id=user_id,
        title=title[:500],
        description=description,
        task_type=task_type,
        due_datetime=due_datetime or None,
        end_datetime=end_datetime or None,
        is_all_day=is_all_day,
        source="manual",
        status="local",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def save_tasks(
    db: Session,
    user_id: str,
    note_id: str,
    tasks: list[dict],
    source: str = "llm",
    status: str = "local",
) -> list[NoteTask]:
    db.query(NoteTask).filter(NoteTask.note_id == note_id, NoteTask.source == source).delete()
    saved = []
    for t in tasks:
        task = NoteTask(
            note_id=note_id,
            user_id=user_id,
            title=t.get("title", "")[:500],
            description=t.get("description", ""),
            task_type=t.get("type", "task"),
            due_datetime=t.get("datetime"),
            end_datetime=t.get("end_datetime"),
            is_all_day=t.get("is_all_day", False),
            source=source,
            status=status,
        )
        db.add(task)
        saved.append(task)
    db.commit()
    return saved


def get_user_tasks(
    db: Session,
    user_id: str,
    done: bool = False,
    status: str | None = None,
) -> list[NoteTask]:
    q = db.query(NoteTask).filter(NoteTask.user_id == user_id, NoteTask.is_done == done)
    if status:
        q = q.filter(NoteTask.status == status)
    else:
        q = q.filter(NoteTask.status != "discovered")
    return q.order_by(NoteTask.created_at.desc()).all()


def get_discovered_tasks(db: Session, user_id: str) -> list[NoteTask]:
    return (
        db.query(NoteTask)
        .filter(NoteTask.user_id == user_id, NoteTask.status == "discovered")
        .order_by(NoteTask.created_at.desc())
        .all()
    )


def confirm_task(db: Session, task_id: str, user_id: str) -> NoteTask | None:
    task = db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).first()
    if task and task.status == "discovered":
        task.status = "local"
        db.commit()
    return task


def dismiss_task(db: Session, task_id: str, user_id: str) -> None:
    db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).delete()
    db.commit()


def set_task_status(db: Session, task_id: str, user_id: str, status: str) -> NoteTask | None:
    task = db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).first()
    if task:
        task.status = status
        db.commit()
    return task


def mark_task_done(db: Session, task_id: str, user_id: str) -> NoteTask | None:
    task = db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).first()
    if task:
        task.is_done = True
        db.commit()
    return task


def unmark_task_done(db: Session, task_id: str, user_id: str) -> NoteTask | None:
    task = db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).first()
    if task:
        task.is_done = False
        db.commit()
    return task


def update_task(
    db: Session,
    task_id: str,
    user_id: str,
    title: str,
    description: str,
    due_datetime: str | None,
    end_datetime: str | None,
    is_all_day: bool,
    task_type: str,
) -> NoteTask | None:
    task = db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).first()
    if task:
        task.title = title[:500]
        task.description = description
        task.due_datetime = due_datetime or None
        task.end_datetime = end_datetime or None
        task.is_all_day = is_all_day
        task.task_type = task_type
        db.commit()
    return task


def delete_task(db: Session, task_id: str, user_id: str) -> None:
    db.query(NoteTask).filter(NoteTask.id == task_id, NoteTask.user_id == user_id).delete()
    db.commit()


def get_done_tasks(db: Session, user_id: str) -> list[NoteTask]:
    return (
        db.query(NoteTask)
        .filter(NoteTask.user_id == user_id, NoteTask.is_done == True)  # noqa: E712
        .order_by(NoteTask.created_at.desc())
        .limit(50)
        .all()
    )
