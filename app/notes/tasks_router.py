from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.models import User
from app.notes.task_service import get_user_tasks, mark_task_done

router = APIRouter(prefix="/tasks")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def tasks_panel(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    pending = get_user_tasks(db, user.id, done=False)
    return templates.TemplateResponse(
        "partials/tasks_panel.html", {"request": request, "tasks": pending}
    )


@router.get("/count", response_class=HTMLResponse)
async def tasks_count(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    count = len(get_user_tasks(db, user.id, done=False))
    if count == 0:
        return HTMLResponse("")
    return HTMLResponse(
        f'<span class="inline-flex items-center justify-center w-4 h-4 text-[10px] '
        f'font-bold bg-[color:var(--accent)] text-white rounded-full">{count}</span>'
    )


@router.post("/{task_id}/done", response_class=HTMLResponse)
async def complete_task(
    task_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    mark_task_done(db, task_id, user.id)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})
