from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.utils import (
    create_access_token,
    decode_access_token,
    validate_password,
    validate_username,
)
from app.database import get_db

router = APIRouter()


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    return service.get_user_by_id(db, user_id)


def require_user(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    errors = {}
    err = validate_username(username)
    if err:
        errors["username"] = err
    err = validate_password(password)
    if err:
        errors["password"] = err
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"
    if not errors and service.get_user_by_username(db, username):
        errors["username"] = "Username already taken"
    if not errors and service.get_user_by_email(db, email):
        errors["email"] = "Email already registered"

    if errors:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "errors": errors,
                "values": {"username": username, "email": email},
            },
            status_code=422,
        )

    service.create_user(db, username, email, password)
    return templates.TemplateResponse(
        request,
        "register.html",
        {"success": "Account created! You can now log in."},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = service.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Invalid username or password",
                "username": username,
            },
            status_code=401,
        )
    if not user.is_verified:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Please verify your email before logging in.",
                "username": username,
            },
            status_code=403,
        )

    token = create_access_token(user.id)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        "access_token", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7
    )
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


@router.get("/verify-email/{token}", response_class=HTMLResponse)
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = service.verify_email_token(db, token)
    if not user:
        return templates.TemplateResponse(
            request,
            "verify_email.html",
            {"error": "Invalid or expired verification link."},
        )
    return templates.TemplateResponse(
        request,
        "verify_email.html",
        {"success": "Email verified! You can now log in."},
    )


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request, email: str = Form(...), db: Session = Depends(get_db)
):
    user = service.get_user_by_email(db, email)
    if user:
        await service.send_password_reset_email(db, user)
    # Always show success to prevent email enumeration
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {
            "success": "If that email exists, a reset link has been sent.",
        },
    )


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(
    request: Request, token: str, db: Session = Depends(get_db)
):
    record = service.verify_reset_token(db, token)
    if not record:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"error": "Invalid or expired reset link."},
        )
    return templates.TemplateResponse(request, "reset_password.html", {"token": token})


@router.post("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    record = service.verify_reset_token(db, token)
    if not record:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"error": "Invalid or expired reset link."},
        )

    errors = {}
    err = validate_password(password)
    if err:
        errors["password"] = err
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"

    if errors:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"errors": errors, "token": token},
            status_code=422,
        )

    service.reset_password(db, record, password)
    return templates.TemplateResponse(
        request,
        "reset_password.html",
        {"success": "Password reset! You can now log in."},
    )
