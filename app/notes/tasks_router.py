from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.models import CalendarToken, NoteTask, User
from app.notes.task_service import (
    create_task,
    delete_task,
    dismiss_task,
    get_discovered_tasks,
    get_done_tasks,
    get_user_tasks,
    mark_task_done,
    set_task_status,
    unmark_task_done,
    update_task,
)

router = APIRouter(prefix="/tasks")
templates = Jinja2Templates(directory="app/templates")

_FILTER_STATUSES = {"local", "google", "microsoft"}


@router.get("", response_class=HTMLResponse)
async def tasks_panel(
    request: Request,
    filter: str = "all",
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    discovered = get_discovered_tasks(db, user.id)

    status = filter if filter in _FILTER_STATUSES else None
    created = get_user_tasks(db, user.id, done=False, status=status)

    providers = [
        t.provider
        for t in db.query(CalendarToken).filter(CalendarToken.user_id == user.id).all()
    ]

    done = get_done_tasks(db, user.id)
    return templates.TemplateResponse(
        "partials/tasks_panel.html",
        {
            "request": request,
            "discovered": discovered,
            "tasks": created,
            "done": done,
            "active_filter": filter,
            "providers": providers,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_task_route(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    due_datetime: str = Form(""),
    end_datetime: str = Form(""),
    is_all_day: str = Form(""),
    task_type: str = Form("task"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not title.strip():
        return HTMLResponse(
            '<p class="text-[11px] text-red-500">Title required</p>', status_code=422
        )
    task = create_task(
        db,
        user.id,
        title.strip(),
        description,
        task_type,
        due_datetime or None,
        end_datetime or None,
        bool(is_all_day),
    )
    providers = [
        t.provider
        for t in db.query(CalendarToken).filter(CalendarToken.user_id == user.id).all()
    ]
    return templates.TemplateResponse(
        "partials/task_card.html",
        {"request": request, "task": task, "providers": providers},
        headers={"HX-Trigger": "taskCountChanged"},
    )


@router.get("/count", response_class=HTMLResponse)
async def tasks_count(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    created = len(get_user_tasks(db, user.id, done=False))
    discovered = len(get_discovered_tasks(db, user.id))
    total = created + discovered
    if total == 0:
        return HTMLResponse("")
    return HTMLResponse(
        f'<span class="inline-flex items-center justify-center w-4 h-4 text-[10px] '
        f'font-bold bg-[color:var(--accent)] text-white rounded-full">{total}</span>'
    )


@router.post("/{task_id}/confirm", response_class=HTMLResponse)
async def confirm_task_route(
    task_id: str,
    title: str = Form(""),
    description: str = Form(""),
    due_datetime: str = Form(""),
    end_datetime: str = Form(""),
    is_all_day: str = Form(""),
    task_type: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    task = (
        db.query(NoteTask)
        .filter(NoteTask.id == task_id, NoteTask.user_id == user.id)
        .first()
    )
    if task and task.status == "discovered":
        if title.strip():
            task.title = title.strip()
        if description is not None:
            task.description = description
        if due_datetime:
            task.due_datetime = due_datetime
        if end_datetime:
            task.end_datetime = end_datetime
        task.is_all_day = bool(is_all_day)
        if task_type:
            task.task_type = task_type
        task.status = "local"
        db.commit()
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})


@router.delete("/{task_id}/dismiss", response_class=HTMLResponse)
async def dismiss_task_route(
    task_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    dismiss_task(db, task_id, user.id)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})


@router.post("/{task_id}/done", response_class=HTMLResponse)
async def complete_task(
    task_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    mark_task_done(db, task_id, user.id)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})


@router.post("/{task_id}/undone", response_class=HTMLResponse)
async def uncomplete_task(
    task_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    unmark_task_done(db, task_id, user.id)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})


@router.delete("/{task_id}", response_class=HTMLResponse)
async def delete_task_route(
    task_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    delete_task(db, task_id, user.id)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})


@router.get("/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(
    request: Request,
    task_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    task = (
        db.query(NoteTask)
        .filter(NoteTask.id == task_id, NoteTask.user_id == user.id)
        .first()
    )
    if not task:
        return HTMLResponse("Not found", status_code=404)
    providers = [
        t.provider
        for t in db.query(CalendarToken).filter(CalendarToken.user_id == user.id).all()
    ]
    return templates.TemplateResponse(
        "partials/task_edit_form.html",
        {"request": request, "task": task, "providers": providers},
    )


@router.put("/{task_id}", response_class=HTMLResponse)
async def update_task_route(
    request: Request,
    task_id: str,
    title: str = Form(...),
    description: str = Form(""),
    due_datetime: str = Form(""),
    end_datetime: str = Form(""),
    is_all_day: str = Form(""),
    task_type: str = Form("task"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    task = update_task(
        db,
        task_id,
        user.id,
        title,
        description,
        due_datetime or None,
        end_datetime or None,
        bool(is_all_day),
        task_type,
    )
    if not task:
        return HTMLResponse("Not found", status_code=404)
    providers = [
        t.provider
        for t in db.query(CalendarToken).filter(CalendarToken.user_id == user.id).all()
    ]
    return templates.TemplateResponse(
        "partials/task_card.html",
        {"request": request, "task": task, "providers": providers},
    )


@router.post("/{task_id}/status", response_class=HTMLResponse)
async def update_task_status(
    task_id: str,
    status: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    set_task_status(db, task_id, user.id, status)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})
