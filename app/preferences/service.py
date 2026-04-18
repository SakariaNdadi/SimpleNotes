from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import UserPreferences

ALLOWED_KEYS = {"font", "palette", "save_ai_summaries", "max_edit_history", "languages"}


def get_or_create_prefs(db: Session, user_id: str) -> UserPreferences:
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def update_prefs(db: Session, user_id: str, **kwargs) -> UserPreferences:
    prefs = get_or_create_prefs(db, user_id)
    for key, value in kwargs.items():
        if key in ALLOWED_KEYS:
            setattr(prefs, key, value)
    db.commit()
    db.refresh(prefs)
    return prefs


def get_languages(prefs: UserPreferences) -> list[str]:
    try:
        return json.loads(prefs.languages)
    except (ValueError, TypeError):
        return ["en"]
