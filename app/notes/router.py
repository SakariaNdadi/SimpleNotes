from fastapi import APIRouter, BackgroundTasks, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.search.hybrid import embed_and_index

from app.auth.router import require_user
from app.database import get_db
from app.labels.service import get_labels
from app.models import CalendarToken, NoteHistory, User
from app.notes import service
from app.notes.nlp_extractor import extract_tasks
from app.notes.task_service import save_tasks
from app.preferences.service import get_or_create_prefs

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
    background_tasks: BackgroundTasks,
    description: str = Form(...),
    label_id: str = Form(""),
    start_datetime: str = Form(""),
    end_datetime: str = Form(""),
    is_all_day: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not description.strip():
        return HTMLResponse('<p class="error">Note cannot be empty</p>', status_code=422)
    note = service.create_note(
        db, user.id, description.strip(), label_id or None,
        start_datetime=start_datetime or None,
        end_datetime=end_datetime or None,
        is_all_day=bool(is_all_day),
    )
    background_tasks.add_task(embed_and_index, note.id, user.id, note.description)
    discovered = _nlp_discover(db, user.id, note.id, note.description)
    labels = get_labels(db, user.id)
    providers = _connected_providers(db, user.id)
    return templates.TemplateResponse(
        "partials/note_timeline_item.html",
        {"request": request, "note": note, "labels": labels, "discovered_tasks": discovered, "providers": providers},
        headers={"HX-Trigger": "noteCreated"},
    )


@router.post("/search", response_class=HTMLResponse)
async def search_notes_local(
    request: Request,
    query: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    from app.labels.service import get_labels
    results = service.search_notes(db, user.id, query.strip()) if query.strip() else []
    labels = get_labels(db, user.id)
    return templates.TemplateResponse(
        "partials/note_list.html",
        {
            "request": request,
            "notes": results,
            "labels": labels,
            "next_offset": 0,
            "has_more": False,
            "label_id": "",
            "is_search": True,
            "is_ai_search": False,
        },
    )


@router.get("/trash", response_class=HTMLResponse)
async def trash_feed(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    notes = service.get_trash(db, user.id)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse(
        "partials/trash_list.html", {"request": request, "notes": notes, "labels": labels}
    )


@router.get("/archive", response_class=HTMLResponse)
async def archive_feed(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    notes = service.get_archive(db, user.id)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse(
        "partials/archive_list.html", {"request": request, "notes": notes, "labels": labels}
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
    return templates.TemplateResponse(
        "partials/note_timeline_item.html", {"request": request, "note": note, "labels": labels}
    )


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
    return templates.TemplateResponse(
        "partials/note_edit_form.html", {"request": request, "note": note, "labels": labels}
    )


@router.get("/{note_id}/history", response_class=HTMLResponse)
async def note_history(
    request: Request,
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(NoteHistory)
        .filter(NoteHistory.note_id == note_id, NoteHistory.user_id == user.id)
        .order_by(NoteHistory.saved_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "partials/note_history_panel.html",
        {"request": request, "entries": entries, "note_id": note_id},
    )


@router.put("/{note_id}", response_class=HTMLResponse)
async def update_note(
    request: Request,
    note_id: str,
    background_tasks: BackgroundTasks,
    description: str = Form(...),
    label_id: str = Form(""),
    start_datetime: str = Form(""),
    end_datetime: str = Form(""),
    is_all_day: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if not note:
        return HTMLResponse("Not found", status_code=404)
    if not description.strip():
        return HTMLResponse('<p class="error">Note cannot be empty</p>', status_code=422)
    prefs = get_or_create_prefs(db, user.id)
    note = service.update_note(
        db, note, description.strip(), label_id or None, max_history=prefs.max_edit_history,
        start_datetime=start_datetime or None,
        end_datetime=end_datetime or None,
        is_all_day=bool(is_all_day),
    )
    background_tasks.add_task(embed_and_index, note.id, user.id, note.description)
    discovered = _nlp_discover(db, user.id, note.id, note.description)
    labels = get_labels(db, user.id)
    providers = _connected_providers(db, user.id)
    return templates.TemplateResponse(
        "partials/note_timeline_item.html",
        {"request": request, "note": note, "labels": labels, "discovered_tasks": discovered, "providers": providers}
    )


@router.post("/{note_id}/archive", response_class=HTMLResponse)
async def archive_note(
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if note:
        service.archive_note(db, note)
    return HTMLResponse("")


@router.post("/{note_id}/restore", response_class=HTMLResponse)
async def restore_note(
    request: Request,
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note_any(db, note_id, user.id)
    if note:
        service.restore_note(db, note)
    return HTMLResponse("")


@router.delete("/{note_id}", response_class=HTMLResponse)
async def delete_note(
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    note = service.get_note(db, note_id, user.id)
    if note:
        service.trash_note(db, note)
    return HTMLResponse("", headers={"HX-Trigger": "taskCountChanged"})


@router.delete("/{note_id}/permanent", response_class=HTMLResponse)
async def permanent_delete(
    note_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    from app.search.meili import delete_note as meili_delete
    note = service.get_note_any(db, note_id, user.id)
    if note:
        service.delete_note(db, note)
        background_tasks.add_task(meili_delete, note_id)
    return HTMLResponse("")


@router.post("/{note_id}/history/{history_id}/restore", response_class=HTMLResponse)
async def restore_from_history(
    request: Request,
    note_id: str,
    history_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    entry = db.query(NoteHistory).filter(
        NoteHistory.id == history_id,
        NoteHistory.note_id == note_id,
        NoteHistory.user_id == user.id,
    ).first()
    note = service.get_note(db, note_id, user.id)
    if not entry or not note:
        return HTMLResponse("Not found", status_code=404)
    prefs = get_or_create_prefs(db, user.id)
    note = service.update_note(
        db, note, entry.description, entry.label_id, max_history=prefs.max_edit_history
    )
    background_tasks.add_task(embed_and_index, note.id, user.id, note.description)
    labels = get_labels(db, user.id)
    return templates.TemplateResponse(
        "partials/note_timeline_item.html", {"request": request, "note": note, "labels": labels, "discovered_tasks": []}
    )


def _connected_providers(db, user_id: str) -> list[str]:
    return [t.provider for t in db.query(CalendarToken).filter(CalendarToken.user_id == user_id).all()]


def _nlp_discover(db, user_id: str, note_id: str, text: str) -> list:
    try:
        tasks = extract_tasks(text)
        if tasks:
            return save_tasks(db, user_id, note_id, tasks, source="nlp", status="discovered")
    except Exception:
        pass
    return []
