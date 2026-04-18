from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.models import CalendarToken, User
from app.notes.task_service import (
    confirm_task,
    dismiss_task,
    get_discovered_tasks,
    get_user_tasks,
    mark_task_done,
    set_task_status,
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

    return templates.TemplateResponse(
        "partials/tasks_panel.html",
        {
            "request": request,
            "discovered": discovered,
            "tasks": created,
            "active_filter": filter,
            "providers": providers,
        },
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
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    confirm_task(db, task_id, user.id)
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


@router.post("/{task_id}/status", response_class=HTMLResponse)
async def update_task_status(
    task_id: str,
    status: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    set_task_status(db, task_id, user.id, status)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})
