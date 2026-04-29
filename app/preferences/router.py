from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.models import User
from app.preferences.service import get_or_create_prefs, update_prefs

router = APIRouter(prefix="/preferences")

AVAILABLE_FONTS = [
    {"id": "inter", "label": "Inter", "css": "Inter, sans-serif"},
    {"id": "serif", "label": "Serif", "css": "Georgia, serif"},
    {"id": "mono", "label": "Monospace", "css": "'Courier New', monospace"},
    {"id": "caveat", "label": "Handwriting", "css": "'Caveat', cursive"},
    {"id": "system", "label": "System UI", "css": "system-ui, sans-serif"},
]

AVAILABLE_LANGUAGES = [
    {"code": "en", "label": "English"},
    {"code": "fr", "label": "French"},
    {"code": "es", "label": "Spanish"},
    {"code": "de", "label": "German"},
    {"code": "ar", "label": "Arabic"},
    {"code": "zh", "label": "Chinese"},
    {"code": "pt", "label": "Portuguese"},
    {"code": "it", "label": "Italian"},
    {"code": "ja", "label": "Japanese"},
    {"code": "ko", "label": "Korean"},
]


@router.get("", response_class=HTMLResponse)
async def get_preferences_panel(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    prefs = get_or_create_prefs(db, user.id)
    import json as _json

    selected_langs = _json.loads(prefs.languages) if prefs.languages else ["en"]
    return templates.TemplateResponse(
        request,
        "partials/preferences_panel.html",
        {
            "prefs": prefs,
            "fonts": AVAILABLE_FONTS,
            "languages": AVAILABLE_LANGUAGES,
            "selected_langs": selected_langs,
        },
    )


@router.post("/font", response_class=HTMLResponse)
async def save_font(
    font: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    update_prefs(db, user.id, font=font)
    return HTMLResponse(
        '<span class="text-xs text-green-600">Saved</span>',
        headers={"HX-Trigger": f'{{"fontChanged": "{font}"}}'},
    )


@router.post("/palette", response_class=HTMLResponse)
async def save_palette(
    palette: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    update_prefs(db, user.id, palette=palette)
    return HTMLResponse('<span class="text-xs text-green-600">Saved</span>')


@router.post("/ai-summary-toggle", response_class=HTMLResponse)
async def toggle_ai_summary(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    val = form.get("save_ai_summaries") == "on"
    update_prefs(db, user.id, save_ai_summaries=val)
    return HTMLResponse('<span class="text-xs text-green-600">Saved</span>')


@router.post("/history-depth", response_class=HTMLResponse)
async def save_history_depth(
    max_edit_history: int = Form(3),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    depth = max(0, min(5, max_edit_history))
    update_prefs(db, user.id, max_edit_history=depth)
    return HTMLResponse('<span class="text-xs text-green-600">Saved</span>')


@router.post("/languages", response_class=HTMLResponse)
async def save_languages(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    langs = form.getlist("languages")
    if not langs:
        langs = ["en"]
    update_prefs(db, user.id, languages=json.dumps(langs))
    return HTMLResponse('<span class="text-xs text-green-600">Saved</span>')
