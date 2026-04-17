from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.database import get_db
from app.models import CalendarToken, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/integrations/panel", response_class=HTMLResponse)
async def integrations_panel(
    request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)
):
    tokens = db.query(CalendarToken).filter(CalendarToken.user_id == user.id).all()
    connected_providers = [t.provider for t in tokens]
    return templates.TemplateResponse(
        "partials/integrations_panel.html",
        {"request": request, "connected_providers": connected_providers},
    )
