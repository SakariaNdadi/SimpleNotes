"""Google Calendar & Tasks integration via OAuth2."""
from __future__ import annotations

from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.auth.utils import decrypt_value
from app.config import get_settings
from app.models import CalendarToken

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
]
REDIRECT_URI_PATH = "/integrations/google/callback"


def get_auth_url(state: str) -> str:
    from google_auth_oauthlib.flow import Flow

    settings = get_settings()
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"{settings.APP_BASE_URL}{REDIRECT_URI_PATH}"],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = f"{settings.APP_BASE_URL}{REDIRECT_URI_PATH}"
    url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state)
    return url


def exchange_code(code: str) -> dict:
    from google_auth_oauthlib.flow import Flow

    settings = get_settings()
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"{settings.APP_BASE_URL}{REDIRECT_URI_PATH}"],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = f"{settings.APP_BASE_URL}{REDIRECT_URI_PATH}"
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": creds.expiry,
        "scope": " ".join(SCOPES),
    }


def _get_creds(token: CalendarToken) -> Credentials:
    settings = get_settings()
    return Credentials(
        token=decrypt_value(token.access_token_encrypted),
        refresh_token=decrypt_value(token.refresh_token_encrypted) if token.refresh_token_encrypted else None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def create_calendar_event(
    token: CalendarToken,
    title: str,
    description: str,
    dt: str | None,
    end_dt: str | None = None,
    is_all_day: bool = False,
) -> dict:
    from datetime import timedelta
    creds = _get_creds(token)
    service = build("calendar", "v3", credentials=creds)
    event = {"summary": title, "description": description}
    if is_all_day:
        start_date = dt[:10] if dt else datetime.now(timezone.utc).date().isoformat()
        end_date = end_dt[:10] if end_dt else start_date
        event["start"] = {"date": start_date}
        event["end"] = {"date": end_date}
    elif dt:
        end = end_dt or (datetime.fromisoformat(dt) + timedelta(hours=1)).isoformat()
        event["start"] = {"dateTime": dt, "timeZone": "UTC"}
        event["end"] = {"dateTime": end, "timeZone": "UTC"}
    else:
        today = datetime.now(timezone.utc).date().isoformat()
        event["start"] = {"date": today}
        event["end"] = {"date": today}
    return service.events().insert(calendarId="primary", body=event).execute()


def create_task(token: CalendarToken, title: str, description: str, due: str | None) -> dict:
    creds = _get_creds(token)
    service = build("tasks", "v1", credentials=creds)
    task = {"title": title, "notes": description}
    if due:
        task["due"] = due
    return service.tasks().insert(tasklist="@default", body=task).execute()
