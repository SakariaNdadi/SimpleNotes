import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32-chars-ok!")
os.environ.setdefault("MEILI_URL", "")
os.environ.setdefault("EMBEDDING_MODEL", "")
os.environ.setdefault("FERNET_KEY", "")
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.config import get_settings
from app.auth.utils import hash_password
from app.database import Base
from app.models import Note, NoteTask, User

get_settings.cache_clear()


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    session = Session(engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def unit_user(db):
    import uuid

    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"unituser_{uid}",
        email=f"unit_{uid}@test.com",
        hashed_password=hash_password("Test1234!"),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def unit_note(db, unit_user):
    note = Note(user_id=unit_user.id, description="Original content")
    db.add(note)
    db.flush()
    return note


@pytest.fixture
def unit_task(db, unit_user, unit_note):
    task = NoteTask(
        note_id=unit_note.id,
        user_id=unit_user.id,
        title="Unit test task",
        status="local",
        source="manual",
    )
    db.add(task)
    db.flush()
    return task
