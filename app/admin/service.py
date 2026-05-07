from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.utils import decrypt_value, encrypt_value, generate_secure_token
from app.config import get_settings
from app.models import (
    ImpersonationAudit,
    Label,
    Note,
    NoteTask,
    OAuthCredential,
    SiteConfig,
    User,
)


def seed_site_config(db: Session) -> None:
    if not db.query(SiteConfig).filter(SiteConfig.id == 1).first():
        db.add(SiteConfig(id=1, registration_open=True))
        db.commit()


def get_site_config(db: Session) -> SiteConfig:
    return db.query(SiteConfig).filter(SiteConfig.id == 1).first()


def update_site_config(db: Session, registration_open: bool) -> SiteConfig:
    config = get_site_config(db)
    config.registration_open = registration_open
    db.commit()
    db.refresh(config)
    return config


def get_dashboard_stats(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()  # noqa: E712
    total_notes = (
        db.query(func.count(Note.id)).filter(Note.is_deleted == False).scalar()  # noqa: E712
    )
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_notes": total_notes,
    }


def get_all_users(
    db: Session, page: int = 1, page_size: int = 25, search: str = ""
) -> tuple[list[dict], int]:
    query = db.query(User)
    if search:
        like = f"%{search}%"
        query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)))
    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for user in users:
        note_count = (
            db.query(func.count(Note.id))
            .filter(Note.user_id == user.id, Note.is_deleted == False)  # noqa: E712
            .scalar()
        )
        result.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "note_count": note_count,
            }
        )
    return result, total


def get_user_detail(db: Session, user_id: str) -> dict | None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    note_count = (
        db.query(func.count(Note.id))
        .filter(Note.user_id == user_id, Note.is_deleted == False)  # noqa: E712
        .scalar()
    )
    label_count = (
        db.query(func.count(Label.id)).filter(Label.user_id == user_id).scalar()
    )
    task_count = (
        db.query(func.count(NoteTask.id)).filter(NoteTask.user_id == user_id).scalar()
    )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "note_count": note_count,
        "label_count": label_count,
        "task_count": task_count,
    }


def deactivate_user(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = False
        db.commit()


def activate_user(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = True
        db.commit()


def _purge_user_fk_refs(db: Session, user_id: str) -> None:
    """Delete rows in tables with user_id FKs that lack ORM cascade from User."""
    db.query(NoteTask).filter(NoteTask.user_id == user_id).delete()
    db.query(ImpersonationAudit).filter(
        (ImpersonationAudit.admin_id == user_id)
        | (ImpersonationAudit.target_user_id == user_id)
    ).delete()


def delete_user(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        _purge_user_fk_refs(db, user_id)
        db.delete(user)
        db.commit()


def bulk_deactivate(db: Session, user_ids: list[str], exclude_id: str) -> int:
    affected = db.query(User).filter(User.id.in_(user_ids), User.id != exclude_id).all()
    for user in affected:
        user.is_active = False
    db.commit()
    return len(affected)


def bulk_delete(db: Session, user_ids: list[str], exclude_id: str) -> int:
    target_ids = [uid for uid in user_ids if uid != exclude_id]
    if not target_ids:
        return 0
    users = db.query(User).filter(User.id.in_(target_ids)).all()
    for uid in target_ids:
        _purge_user_fk_refs(db, uid)
    for user in users:
        db.delete(user)
    db.commit()
    return len(users)


def admin_reset_password(db: Session, user_id: str) -> str:
    from app.models import PasswordResetToken

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return ""
    from datetime import timedelta

    raw, hashed = generate_secure_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
    db.add(PasswordResetToken(user_id=user_id, token_hash=hashed, expires_at=expires))
    db.commit()
    settings = get_settings()
    return f"{settings.APP_BASE_URL}/reset-password/{raw}"


def start_impersonation(
    db: Session, admin: User, target_user_id: str
) -> ImpersonationAudit:
    audit = ImpersonationAudit(admin_id=admin.id, target_user_id=target_user_id)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def stop_impersonation(db: Session, audit_id: int) -> None:
    audit = (
        db.query(ImpersonationAudit).filter(ImpersonationAudit.id == audit_id).first()
    )
    if audit and not audit.ended_at:
        audit.ended_at = datetime.now(timezone.utc)
        db.commit()


def get_oauth_credentials(db: Session) -> list[OAuthCredential]:
    return db.query(OAuthCredential).all()


def upsert_oauth_credential(
    db: Session,
    provider: str,
    client_id: str,
    client_secret: str,
    tenant_id: str | None = None,
) -> OAuthCredential:
    record = (
        db.query(OAuthCredential).filter(OAuthCredential.provider == provider).first()
    )
    if not record:
        record = OAuthCredential(provider=provider)
        db.add(record)
    record.client_id = client_id
    record.client_secret_encrypted = encrypt_value(client_secret)
    record.tenant_id = tenant_id
    db.commit()
    db.refresh(record)
    return record


def get_integration_creds(db: Session, provider: str) -> dict:
    settings = get_settings()
    record = (
        db.query(OAuthCredential).filter(OAuthCredential.provider == provider).first()
    )
    if record:
        return {
            "client_id": record.client_id,
            "client_secret": decrypt_value(record.client_secret_encrypted),
            "tenant_id": record.tenant_id,
        }
    if provider == "google":
        return {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "tenant_id": None,
        }
    if provider == "microsoft":
        return {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "tenant_id": settings.MICROSOFT_TENANT_ID,
        }
    return {}


def get_env_status(db: Session) -> dict:
    settings = get_settings()
    google_creds = get_integration_creds(db, "google")
    microsoft_creds = get_integration_creds(db, "microsoft")
    return {
        "database_url": _mask_url(settings.DATABASE_URL),
        "is_postgres": settings.is_postgres,
        "smtp_configured": bool(settings.MAIL_USERNAME),
        "meili_configured": bool(settings.MEILI_URL),
        "rabbitmq_configured": bool(settings.RABBITMQ_URL),
        "embedding_model": settings.EMBEDDING_MODEL or "not set",
        "app_base_url": settings.APP_BASE_URL,
        "google_configured": bool(google_creds.get("client_id")),
        "microsoft_configured": bool(microsoft_creds.get("client_id")),
        "google_from_db": db.query(OAuthCredential)
        .filter(OAuthCredential.provider == "google")
        .count()
        > 0,
        "microsoft_from_db": db.query(OAuthCredential)
        .filter(OAuthCredential.provider == "microsoft")
        .count()
        > 0,
    }


def _mask_url(url: str) -> str:
    if "://" in url and "@" in url:
        scheme, rest = url.split("://", 1)
        host_part = rest.split("@", 1)[1]
        return f"{scheme}://****:****@{host_part}"
    return url
