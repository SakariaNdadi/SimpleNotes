import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.config import get_settings

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")


def _prehash(password: str) -> bytes:
    """SHA-256 pre-hash → always 32 bytes, safe for bcrypt's 72-byte limit."""
    return hashlib.sha256(password.encode()).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prehash(plain), hashed.encode())


def validate_username(username: str) -> str | None:
    """Return error string or None if valid."""
    if not USERNAME_RE.match(username):
        return "Username must be 3-20 chars, letters/numbers/underscore only"
    return None


def validate_password(password: str) -> str | None:
    """Return error string or None if valid."""
    if not PASSWORD_RE.match(password):
        return "Password must be 8+ chars with at least 1 uppercase letter and 1 digit"
    return None


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None


def generate_secure_token() -> tuple[str, str]:
    """Return (raw_token, hashed_token). Store hash, send raw."""
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.FERNET_KEY
    if not key:
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
