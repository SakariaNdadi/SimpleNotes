from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.labels import service
from app.models import User

router = APIRouter(prefix="/labels")


@router.get("", response_class=HTMLResponse)
async def list_labels(
    request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)
):
    labels = service.get_labels(db, user.id)
    return templates.TemplateResponse(
        request, "partials/label_list.html", {"labels": labels}
    )


@router.post("", response_class=HTMLResponse)
async def create_label(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    color: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not title.strip():
        return HTMLResponse('<p class="error">Title is required</p>', status_code=422)
    result = service.create_label(db, user.id, title, description, color)
    if isinstance(result, str):
        return HTMLResponse(f'<p class="error">{result}</p>', status_code=422)
    labels = service.get_labels(db, user.id)
    return templates.TemplateResponse(
        request, "partials/label_list.html", {"labels": labels}
    )


@router.put("/{label_id}", response_class=HTMLResponse)
async def update_label(
    request: Request,
    label_id: str,
    title: str = Form(...),
    description: str = Form(""),
    color: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    label = service.get_label(db, label_id, user.id)
    if not label:
        return HTMLResponse("Not found", status_code=404)
    if not title.strip():
        return HTMLResponse('<p class="error">Title is required</p>', status_code=422)
    result = service.update_label(db, label, title, description, color)
    if isinstance(result, str):
        return HTMLResponse(f'<p class="error">{result}</p>', status_code=422)
    return templates.TemplateResponse(
        request, "partials/label_item.html", {"label": result}
    )


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
