from datetime import datetime, timedelta, timezone

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from sqlalchemy.orm import Session

from app.auth.utils import (
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.config import get_settings
from app.models import EmailVerificationToken, PasswordResetToken, User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, email: str, password: str) -> User:
    user = User(username=username, email=email, hashed_password=hash_password(password), is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def _mail_config() -> ConnectionConfig:
    s = get_settings()
    return ConnectionConfig(
        MAIL_USERNAME=s.MAIL_USERNAME,
        MAIL_PASSWORD=s.MAIL_PASSWORD,
        MAIL_FROM=s.MAIL_FROM,
        MAIL_PORT=s.MAIL_PORT,
        MAIL_SERVER=s.MAIL_SERVER,
        MAIL_STARTTLS=s.MAIL_STARTTLS,
        MAIL_SSL_TLS=s.MAIL_SSL_TLS,
        USE_CREDENTIALS=bool(s.MAIL_USERNAME),
    )


async def send_verification_email(db: Session, user: User) -> None:
    raw, hashed = generate_secure_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    # Remove old tokens
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id
    ).delete()
    db.add(
        EmailVerificationToken(user_id=user.id, token_hash=hashed, expires_at=expires)
    )
    db.commit()

    settings = get_settings()
    link = f"{settings.APP_BASE_URL}/verify-email/{raw}"

    if not settings.MAIL_USERNAME:
        print(f"[DEV] Email verify link: {link}")
        return

    msg = MessageSchema(
        subject="Verify your Notes account",
        recipients=[user.email],
        body=f"Click to verify: {link}\n\nExpires in 24 hours.",
        subtype=MessageType.plain,
    )
    await FastMail(_mail_config()).send_message(msg)


async def send_password_reset_email(db: Session, user: User) -> None:
    raw, hashed = generate_secure_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashed, expires_at=expires))
    db.commit()

    settings = get_settings()
    link = f"{settings.APP_BASE_URL}/reset-password/{raw}"

    if not settings.MAIL_USERNAME:
        print(f"[DEV] Password reset link: {link}")
        return

    msg = MessageSchema(
        subject="Reset your Notes password",
        recipients=[user.email],
        body=f"Click to reset: {link}\n\nExpires in 1 hour.",
        subtype=MessageType.plain,
    )
    await FastMail(_mail_config()).send_message(msg)


def verify_email_token(db: Session, raw_token: str) -> User | None:
    hashed = hash_token(raw_token)
    record = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == hashed)
        .first()
    )
    if not record or record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        return None
    user = get_user_by_id(db, record.user_id)
    if user:
        user.is_verified = True
        db.delete(record)
        db.commit()
    return user


def verify_reset_token(db: Session, raw_token: str) -> PasswordResetToken | None:
    hashed = hash_token(raw_token)
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == hashed,
            PasswordResetToken.used,
        )
        .first()
    )
    if not record or record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        return None
    return record


def reset_password(db: Session, record: PasswordResetToken, new_password: str) -> None:
    user = get_user_by_id(db, record.user_id)
    user.hashed_password = hash_password(new_password)
    record.used = True
    db.commit()
