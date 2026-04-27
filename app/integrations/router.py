import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.auth.utils import encrypt_value
from app.database import get_db
from app.models import CalendarToken, User

router = APIRouter(prefix="/integrations")


def _get_or_create_token(
    db: Session, user_id: str, provider: str, token_data: dict
) -> CalendarToken:
    record = (
        db.query(CalendarToken)
        .filter(
            CalendarToken.user_id == user_id,
            CalendarToken.provider == provider,
        )
        .first()
    )
    if not record:
        record = CalendarToken(user_id=user_id, provider=provider)
        db.add(record)

    record.access_token_encrypted = encrypt_value(token_data["access_token"])
    record.refresh_token_encrypted = (
        encrypt_value(token_data["refresh_token"])
        if token_data.get("refresh_token")
        else None
    )
    record.expires_at = token_data.get("expires_at")
    record.scope = token_data.get("scope")
    db.commit()
    return record


# ── Google ────────────────────────────────────────────────────────────────────


@router.get("/google/oauth")
async def google_oauth_start(request: Request, user: User = Depends(require_user)):
    from app.integrations.google import get_auth_url

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    request.session["oauth_user_id"] = user.id
    return RedirectResponse(get_auth_url(state))


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    db: Session = Depends(get_db),
):
    from app.integrations.google import exchange_code

    if not code:
        return RedirectResponse("/?error=google_oauth_failed")
    token_data = exchange_code(code)
    user_id = request.session.get("oauth_user_id")
    _get_or_create_token(db, user_id, "google", token_data)
    return RedirectResponse("/?connected=google")


# ── Microsoft ─────────────────────────────────────────────────────────────────


@router.get("/microsoft/oauth")
async def microsoft_oauth_start(request: Request, user: User = Depends(require_user)):
    from app.integrations.microsoft import get_auth_url

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    request.session["oauth_user_id"] = user.id
    return RedirectResponse(get_auth_url(state))


@router.get("/microsoft/callback")
async def microsoft_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    db: Session = Depends(get_db),
):
    from app.integrations.microsoft import exchange_code

    if not code:
        return RedirectResponse("/?error=microsoft_oauth_failed")
    token_data = exchange_code(code)
    user_id = request.session.get("oauth_user_id")
    _get_or_create_token(db, user_id, "microsoft", token_data)
    return RedirectResponse("/?connected=microsoft")


# ── Create task/event ─────────────────────────────────────────────────────────


@router.post("/{provider}/create-task", response_class=HTMLResponse)
async def create_task(
    request: Request,
    provider: str,
    title: str = Form(...),
    description: str = Form(""),
    dt: str = Form(""),
    end_dt: str = Form(""),
    is_all_day: str = Form(""),
    task_type: str = Form("task"),  # "task" | "event"
    task_id: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    token = (
        db.query(CalendarToken)
        .filter(
            CalendarToken.user_id == user.id,
            CalendarToken.provider == provider,
        )
        .first()
    )
    if not token:
        return HTMLResponse(
            f'<p class="error">{provider} not connected</p>', status_code=400
        )

    all_day = bool(is_all_day)
    try:
        if provider == "google":
            from app.integrations.google import (
                create_calendar_event,
                create_task as g_task,
            )

            if task_type == "event":
                create_calendar_event(
                    token, title, description, dt or None, end_dt or None, all_day
                )
            else:
                g_task(token, title, description, dt or None)
        elif provider == "microsoft":
            from app.integrations.microsoft import (
                create_calendar_event as ms_event,
                create_task as ms_task,
            )

            if task_type == "event":
                ms_event(token, title, description, dt or None, end_dt or None, all_day)
            else:
                ms_task(token, title, description, dt or None)
    except Exception as e:
        return HTMLResponse(f'<p class="error">Failed: {e}</p>', status_code=500)

    if task_id:
        from app.notes.task_service import set_task_status

        set_task_status(db, task_id, user.id, provider)

    return HTMLResponse('<p class="success">Created successfully!</p>')


@router.delete("/{provider}/disconnect", response_class=HTMLResponse)
async def disconnect_provider(
    request: Request,
    provider: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    db.query(CalendarToken).filter(
        CalendarToken.user_id == user.id,
        CalendarToken.provider == provider,
    ).delete()
    db.commit()
    return HTMLResponse(f'<p class="success">{provider.title()} disconnected</p>')
