from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.ai.router import router as ai_router
from app.auth.profile_router import router as profile_router
from app.auth.router import get_current_user, router as auth_router
from app.config import get_settings
from app.database import create_tables, get_db
from app.integrations.panel_router import router as integrations_panel_router
from app.integrations.router import router as integrations_router
from app.labels.router import router as labels_router
from app.notes.router import router as notes_router
from app.notes.tasks_router import router as tasks_router
from app.preferences.router import router as preferences_router

settings = get_settings()

app = FastAPI(title="Notes", version="1.0.0", docs_url="/api/docs")

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(notes_router)
app.include_router(labels_router)
app.include_router(ai_router)
app.include_router(integrations_router)
app.include_router(integrations_panel_router)
app.include_router(tasks_router)
app.include_router(preferences_router)


# def _apply_migrations():
#     with engine.connect() as conn:
#         existing = {row[1] for row in conn.execute(text("PRAGMA table_info(notes)"))}
#         new_cols = {
#             "is_deleted": "INTEGER NOT NULL DEFAULT 0",
#             "deleted_at": "DATETIME",
#             "is_archived": "INTEGER NOT NULL DEFAULT 0",
#         }
#         for col, definition in new_cols.items():
#             if col not in existing:
#                 conn.execute(text(f"ALTER TABLE notes ADD COLUMN {col} {definition}"))
#         conn.commit()


@app.on_event("startup")
async def on_startup():
    create_tables()
    # _apply_migrations()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    from app.labels.service import get_labels
    from app.preferences.service import get_or_create_prefs

    labels = get_labels(db, user.id)
    prefs = get_or_create_prefs(db, user.id)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user, "labels": labels, "prefs": prefs},
    )
