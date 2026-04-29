from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from sqlalchemy.orm import Session

from app.auth.router import require_user
from app.auth.service import get_user_by_email, get_user_by_username
from app.auth.utils import (
    hash_password,
    validate_password,
    validate_username,
    verify_password,
)
from app.database import get_db
from app.models import User

router = APIRouter()


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(request, "partials/profile.html", {"user": user})


@router.post("/profile", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    errors = {}

    if not verify_password(current_password, user.hashed_password):
        errors["current_password"] = "Incorrect current password"

    if username != user.username:
        err = validate_username(username)
        if err:
            errors["username"] = err
        elif get_user_by_username(db, username):
            errors["username"] = "Username already taken"

    if email != user.email:
        if get_user_by_email(db, email):
            errors["email"] = "Email already in use"

    if new_password:
        err = validate_password(new_password)
        if err:
            errors["new_password"] = err
        elif new_password != confirm_password:
            errors["confirm_password"] = "Passwords do not match"

    if errors:
        return templates.TemplateResponse(
            request,
            "partials/profile.html",
            {"user": user, "errors": errors},
            status_code=422,
        )

    user.username = username
    if email != user.email:
        user.email = email
        user.is_verified = False
    if new_password:
        user.hashed_password = hash_password(new_password)
    db.commit()

    return templates.TemplateResponse(
        request,
        "partials/profile.html",
        {"user": user, "success": "Profile updated"},
    )
