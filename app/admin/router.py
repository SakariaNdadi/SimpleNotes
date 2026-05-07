from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.admin import service as admin_service
from app.auth.router import require_admin
from app.auth.utils import decrypt_value
from app.database import get_db
from app.models import OAuthCredential, User
from app.templates_config import templates

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stats = admin_service.get_dashboard_stats(db)
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"admin": admin, "stats": stats},
    )


@router.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    page: int = 1,
    search: str = "",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    page_size = 25
    users, total = admin_service.get_all_users(
        db, page=page, page_size=page_size, search=search
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "admin": admin,
            "users": users,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "search": search,
        },
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user_data = admin_service.get_user_detail(db, user_id)
    if not user_data:
        return RedirectResponse("/admin/users", status_code=302)
    return templates.TemplateResponse(
        request,
        "admin/user_detail.html",
        {"admin": admin, "user_data": user_data},
    )


@router.post("/users/{user_id}/deactivate", response_class=HTMLResponse)
async def deactivate_user(
    request: Request,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        return RedirectResponse(
            f"/admin/users/{user_id}?error=cannot_deactivate_self", status_code=303
        )
    admin_service.deactivate_user(db, user_id)
    return RedirectResponse(
        f"/admin/users/{user_id}?success=deactivated", status_code=303
    )


@router.post("/users/{user_id}/activate", response_class=HTMLResponse)
async def activate_user(
    request: Request,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    admin_service.activate_user(db, user_id)
    return RedirectResponse(
        f"/admin/users/{user_id}?success=activated", status_code=303
    )


@router.post("/users/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: str,
    confirm: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        return RedirectResponse(
            f"/admin/users/{user_id}?error=cannot_delete_self", status_code=303
        )
    if confirm != "DELETE":
        return RedirectResponse(
            f"/admin/users/{user_id}?error=confirm_required", status_code=303
        )
    admin_service.delete_user(db, user_id)
    return RedirectResponse("/admin/users?success=deleted", status_code=303)


@router.post("/users/bulk-action")
async def bulk_action(
    request: Request,
    action: str = Form(...),
    user_ids: list[str] = Form(default=[]),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not user_ids:
        return RedirectResponse("/admin/users?error=no_selection", status_code=303)
    if action == "deactivate":
        admin_service.bulk_deactivate(db, user_ids, exclude_id=admin.id)
        return RedirectResponse("/admin/users?success=deactivated", status_code=303)
    if action == "delete":
        admin_service.bulk_delete(db, user_ids, exclude_id=admin.id)
        return RedirectResponse("/admin/users?success=deleted", status_code=303)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/reset-password", response_class=HTMLResponse)
async def reset_user_password(
    request: Request,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    reset_link = admin_service.admin_reset_password(db, user_id)
    user_data = admin_service.get_user_detail(db, user_id)
    return templates.TemplateResponse(
        request,
        "admin/user_detail.html",
        {"admin": admin, "user_data": user_data, "reset_link": reset_link},
    )


@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    request: Request,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    audit = admin_service.start_impersonation(db, admin, user_id)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("impersonating_user_id", user_id, httponly=True, samesite="lax")
    resp.set_cookie(
        "impersonation_audit_id", str(audit.id), httponly=True, samesite="lax"
    )
    return resp


@router.post("/impersonate/stop")
async def stop_impersonation(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    audit_id = request.cookies.get("impersonation_audit_id")
    if audit_id and audit_id.isdigit():
        admin_service.stop_impersonation(db, int(audit_id))
    resp = RedirectResponse("/admin", status_code=303)
    resp.delete_cookie("impersonating_user_id")
    resp.delete_cookie("impersonation_audit_id")
    return resp


@router.get("/settings", response_class=HTMLResponse)
async def site_settings(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    site_config = admin_service.get_site_config(db)
    env_status = admin_service.get_env_status(db)
    return templates.TemplateResponse(
        request,
        "admin/site_settings.html",
        {"admin": admin, "site_config": site_config, "env_status": env_status},
    )


@router.post("/settings")
async def update_site_settings(
    request: Request,
    registration_open: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    admin_service.update_site_config(db, registration_open == "on")
    return RedirectResponse("/admin/settings?success=saved", status_code=303)


@router.get("/oauth", response_class=HTMLResponse)
async def oauth_settings(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    credentials = admin_service.get_oauth_credentials(db)
    creds_by_provider = {c.provider: c for c in credentials}
    return templates.TemplateResponse(
        request,
        "admin/oauth_settings.html",
        {"admin": admin, "creds_by_provider": creds_by_provider},
    )


@router.post("/oauth/{provider}")
async def upsert_oauth_credential(
    request: Request,
    provider: str,
    client_id: str = Form(...),
    client_secret: str = Form(...),
    tenant_id: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if provider not in ("google", "microsoft"):
        return RedirectResponse("/admin/oauth?error=invalid_provider", status_code=303)

    existing = db.query(OAuthCredential).filter_by(provider=provider).first()
    if not client_secret and existing:
        client_secret = decrypt_value(existing.client_secret_encrypted)

    admin_service.upsert_oauth_credential(
        db,
        provider=provider,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id or None,
    )
    return RedirectResponse("/admin/oauth?success=saved", status_code=303)
