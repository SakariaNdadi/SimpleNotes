from datetime import date, datetime

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _humanize_date(dt: datetime) -> str:
    if dt is None:
        return ""
    today = date.today()
    note_date = dt.date()
    delta = (today - note_date).days
    time_str = dt.strftime("%H:%M")

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


templates.env.filters["humanize_date"] = _humanize_date
