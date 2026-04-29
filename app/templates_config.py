from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import HTMLResponse

_VALID_TIMEZONES = available_timezones()


def _resolve_timezone(tz_str: str) -> ZoneInfo:
    if tz_str in _VALID_TIMEZONES:
        try:
            return ZoneInfo(tz_str)
        except ZoneInfoNotFoundError:
            pass
    return ZoneInfo("UTC")


def _local_dt(dt: datetime, tz_str: str = "UTC") -> datetime:
    if dt is None:
        return dt
    return dt.astimezone(_resolve_timezone(tz_str))


def _humanize_date(dt: datetime, tz_str: str = "UTC") -> str:
    if dt is None:
        return ""
    tz = _resolve_timezone(tz_str)
    local = dt.astimezone(tz)
    today = datetime.now(tz).date()
    note_date = local.date()
    delta = (today - note_date).days
    time_str = local.strftime("%H:%M")

    if delta == 0:
        return f"Today · {time_str}"
    if delta == 1:
        return f"Yesterday · {time_str}"
    if delta < 7:
        return f"{delta} days ago · {time_str}"
    if delta < 14:
        return f"Last week · {time_str}"
    if today.year == note_date.year and today.month == note_date.month:
        return f"This month on the {note_date.day} · {time_str}"
    if delta <= 60:
        return f"Last month on the {note_date.day} · {time_str}"
    if today.year == note_date.year:
        return f"{note_date.strftime('%b')} {note_date.day} · {time_str}"
    return f"{note_date.strftime('%b')} {note_date.day}, {note_date.year} · {time_str}"


class _TimezoneTemplates(Jinja2Templates):
    def TemplateResponse(
        self,
        *args,
        **kwargs,
    ) -> HTMLResponse:
        if args and isinstance(args[0], Request):
            request: Request = args[0]
            context: dict = args[2] if len(args) > 2 else kwargs.get("context", {})
        else:
            context = args[1] if len(args) > 1 else kwargs.get("context", {})
            request = context.get("request")

        if request is not None and "user_tz" not in context:
            raw_tz = request.cookies.get("tz", "UTC")
            context["user_tz"] = raw_tz if raw_tz in _VALID_TIMEZONES else "UTC"

        return super().TemplateResponse(*args, **kwargs)


templates = _TimezoneTemplates(directory="app/templates")
templates.env.filters["humanize_date"] = _humanize_date
templates.env.filters["local_dt"] = _local_dt
