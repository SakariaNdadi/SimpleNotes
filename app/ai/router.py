from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.ai import service as ai_service
from app.auth.router import require_user
from app.auth.utils import encrypt_value
from app.database import get_db
from app.models import User, UserLLMConfig
from app.notes.service import get_notes

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ── LLM Settings ─────────────────────────────────────────────────────────────

@router.get("/settings/llm", response_class=HTMLResponse)
async def llm_settings_page(
    request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)
):
    configs = db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user.id).all()
    return templates.TemplateResponse("partials/llm_settings.html", {"request": request, "configs": configs})


@router.post("/settings/llm", response_class=HTMLResponse)
async def add_llm_config(
    request: Request,
    provider_name: str = Form(...),
    model_name: str = Form(...),
    base_url: str = Form(""),
    api_key: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    # Deactivate all existing configs for this user
    db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user.id).update({"is_active": False})
    config = UserLLMConfig(
        user_id=user.id,
        provider_name=provider_name.strip(),
        model_name=model_name.strip(),
        base_url=base_url.strip() or None,
        api_key_encrypted=encrypt_value(api_key) if api_key else None,
        is_active=True,
    )
    db.add(config)
    db.commit()

    configs = db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user.id).all()
    return templates.TemplateResponse(
        "partials/llm_settings.html",
        {"request": request, "configs": configs, "success": "LLM config saved and set as active"},
    )


@router.delete("/settings/llm/{config_id}", response_class=HTMLResponse)
async def delete_llm_config(
    request: Request,
    config_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    config = db.query(UserLLMConfig).filter(UserLLMConfig.id == config_id, UserLLMConfig.user_id == user.id).first()
    if config:
        db.delete(config)
        db.commit()
    configs = db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user.id).all()
    return templates.TemplateResponse("partials/llm_settings.html", {"request": request, "configs": configs})


@router.post("/settings/llm/{config_id}/activate", response_class=HTMLResponse)
async def activate_llm_config(
    request: Request,
    config_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user.id).update({"is_active": False})
    config = db.query(UserLLMConfig).filter(UserLLMConfig.id == config_id, UserLLMConfig.user_id == user.id).first()
    if config:
        config.is_active = True
        db.commit()
    configs = db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user.id).all()
    return templates.TemplateResponse("partials/llm_settings.html", {"request": request, "configs": configs})


# ── AI Endpoints ──────────────────────────────────────────────────────────────

@router.post("/ai/summary/{note_id}", response_class=HTMLResponse)
async def summarize_note(
    request: Request,
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    from app.notes.service import get_note
    note = get_note(db, note_id, user.id)
    if not note:
        return HTMLResponse("Not found", status_code=404)
    summary = await ai_service.summarize_note(db, user.id, note.description)
    return templates.TemplateResponse(
        "partials/ai_summary.html", {"request": request, "summary": summary, "note_id": note_id}
    )


@router.post("/ai/search", response_class=HTMLResponse)
async def ai_search(
    request: Request,
    query: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    all_notes = get_notes(db, user.id, limit=100)
    results = await ai_service.semantic_search(db, user.id, query, all_notes)
    from app.labels.service import get_labels
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
        },
    )


@router.post("/ai/detect-tasks/{note_id}", response_class=HTMLResponse)
async def detect_tasks(
    request: Request,
    note_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    from app.notes.service import get_note
    note = get_note(db, note_id, user.id)
    if not note:
        return HTMLResponse("")
    tasks = await ai_service.detect_tasks(db, user.id, note.description)
    if not tasks:
        return HTMLResponse("")
    from app.models import CalendarToken
    connected = db.query(CalendarToken).filter(CalendarToken.user_id == user.id).all()
    providers = [t.provider for t in connected]
    return templates.TemplateResponse(
        "partials/task_prompt.html",
        {"request": request, "tasks": tasks, "note_id": note_id, "providers": providers},
    )
