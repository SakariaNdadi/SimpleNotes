from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.labels.service import get_labels
from app.models import User
from app.notes import service

router = APIRouter(prefix="/notes")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def list_notes(
    request: Request,
    offset: int = 0,
    label_id: str = "",
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    notes = service.get_notes(db, user.id, offset=offset, label_id=label_id or None)
    labels = get_labels(db, user.id)
    next_offset = offset + len(notes)
    has_more = len(notes) == 20
    return templates.TemplateResponse(
        "partials/note_list.html",
        {
            "request": request,
            "notes": notes,
            "labels": labels,
            "next_offset": next_offset,
            "has_more": has_more,
            "label_id": label_id,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_note(
    request: Request,
    description: str = Form(...),
    label_id: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not description.strip():
        return HTMLResponse('<p class="error">Note cannot be empty</p>', status_code=422)
    note = service.create_note(db, user.id, description.strip(), label_id or None)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse(
        "partials/note_card.html",
        {"request": request, "note": note, "labels": labels},
        headers={"HX-Trigger": "noteCreated"},
    )


@router.get("/{note_id}", response_class=HTMLResponse)
async def get_note_card(
    request: Request,
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if not note:
        return HTMLResponse("Not found", status_code=404)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse("partials/note_card.html", {"request": request, "note": note, "labels": labels})


@router.get("/{note_id}/edit", response_class=HTMLResponse)
async def edit_note_form(
    request: Request,
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if not note:
        return HTMLResponse("Not found", status_code=404)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse("partials/note_edit_form.html", {"request": request, "note": note, "labels": labels})


@router.put("/{note_id}", response_class=HTMLResponse)
async def update_note(
    request: Request,
    note_id: str,
    description: str = Form(...),
    label_id: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if not note:
        return HTMLResponse("Not found", status_code=404)
    if not description.strip():
        return HTMLResponse('<p class="error">Note cannot be empty</p>', status_code=422)
    note = service.update_note(db, note, description.strip(), label_id or None)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse("partials/note_card.html", {"request": request, "note": note, "labels": labels})


@router.delete("/{note_id}", response_class=HTMLResponse)
async def delete_note(
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if note:
        service.delete_note(db, note)
    return HTMLResponse("")
