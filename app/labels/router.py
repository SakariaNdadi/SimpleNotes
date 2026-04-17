from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.labels import service
from app.models import User

router = APIRouter(prefix="/labels")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def list_labels(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    labels = service.get_labels(db, user.id)
    return templates.TemplateResponse("partials/label_list.html", {"request": request, "labels": labels})


@router.post("", response_class=HTMLResponse)
async def create_label(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not title.strip():
        return HTMLResponse('<p class="error">Title is required</p>', status_code=422)
    result = service.create_label(db, user.id, title, description)
    if isinstance(result, str):
        return HTMLResponse(f'<p class="error">{result}</p>', status_code=422)
    labels = service.get_labels(db, user.id)
    return templates.TemplateResponse("partials/label_list.html", {"request": request, "labels": labels})


@router.put("/{label_id}", response_class=HTMLResponse)
async def update_label(
    request: Request,
    label_id: str,
    title: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    label = service.get_label(db, label_id, user.id)
    if not label:
        return HTMLResponse("Not found", status_code=404)
    if not title.strip():
        return HTMLResponse('<p class="error">Title is required</p>', status_code=422)
    result = service.update_label(db, label, title, description)
    if isinstance(result, str):
        return HTMLResponse(f'<p class="error">{result}</p>', status_code=422)
    return templates.TemplateResponse("partials/label_item.html", {"request": request, "label": result})


@router.delete("/{label_id}", response_class=HTMLResponse)
async def delete_label(
    label_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    label = service.get_label(db, label_id, user.id)
    if label:
        service.delete_label(db, label)
    return HTMLResponse("")
