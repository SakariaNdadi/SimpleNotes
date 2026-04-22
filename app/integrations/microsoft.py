"""Microsoft Graph Calendar & To Do integration via OAuth2 (MSAL)."""

from __future__ import annotations

import httpx
import msal

from app.auth.utils import decrypt_value
from app.config import get_settings
from app.models import CalendarToken

SCOPES = ["Calendars.ReadWrite", "Tasks.ReadWrite", "offline_access"]
REDIRECT_URI_PATH = "/integrations/microsoft/callback"


def _get_app() -> msal.ConfidentialClientApplication:
    s = get_settings()
    return msal.ConfidentialClientApplication(
        s.MICROSOFT_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{s.MICROSOFT_TENANT_ID}",
        client_credential=s.MICROSOFT_CLIENT_SECRET,
    )


def get_auth_url(state: str) -> str:
    s = get_settings()
    app = _get_app()
    return app.get_authorization_request_url(
        scopes=SCOPES,
        state=state,
        redirect_uri=f"{s.APP_BASE_URL}{REDIRECT_URI_PATH}",
    )


def exchange_code(code: str) -> dict:
    s = get_settings()
    app = _get_app()
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=f"{s.APP_BASE_URL}{REDIRECT_URI_PATH}",
    )
    if "error" in result:
        raise ValueError(result.get("error_description", result["error"]))
    return {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "expires_at": None,
        "scope": " ".join(SCOPES),
    }


def _headers(token: CalendarToken) -> dict:
    access = decrypt_value(token.access_token_encrypted)
    return {"Authorization": f"Bearer {access}", "Content-Type": "application/json"}


def create_calendar_event(
    token: CalendarToken,
    title: str,
    description: str,
    dt: str | None,
    end_dt: str | None = None,
    is_all_day: bool = False,
) -> dict:
    from datetime import datetime, timedelta, timezone

    if is_all_day:
        start_date = dt[:10] if dt else datetime.now(timezone.utc).date().isoformat()
        end_date = end_dt[:10] if end_dt else start_date
        body = {
            "subject": title,
            "body": {"contentType": "text", "content": description},
            "isAllDay": True,
            "start": {"dateTime": f"{start_date}T00:00:00", "timeZone": "UTC"},
            "end": {"dateTime": f"{end_date}T00:00:00", "timeZone": "UTC"},
        }
    else:
        start = dt or datetime.now(timezone.utc).isoformat()
        end = end_dt or (datetime.fromisoformat(start) + timedelta(hours=1)).isoformat()
        body = {
            "subject": title,
            "body": {"contentType": "text", "content": description},
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
        }
    with httpx.Client() as client:
        resp = client.post(
            "https://graph.microsoft.com/v1.0/me/events",
            json=body,
            headers=_headers(token),
        )
        resp.raise_for_status()
        return resp.json()


def create_task(
    token: CalendarToken, title: str, description: str, due: str | None
) -> dict:
    body: dict = {
        "title": title,
        "body": {"content": description, "contentType": "text"},
    }
    if due:
        body["dueDateTime"] = {"dateTime": due, "timeZone": "UTC"}
    with httpx.Client() as client:
        resp = client.post(
            "https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks",
            json=body,
            headers=_headers(token),
        )
        resp.raise_for_status()
        return resp.json()
