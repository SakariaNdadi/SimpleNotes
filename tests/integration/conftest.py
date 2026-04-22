import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth.utils import create_access_token, hash_password
from app.config import get_settings
from app.database import Base, get_db
from app.models import Note, NoteTask, User
from main import app

# Must be set before any app imports so get_settings() picks them up.
_TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://notes:notes@localhost:5433/notes_test",
)
os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ.setdefault("MEILI_URL", "")
os.environ.setdefault("EMBEDDING_MODEL", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long-ok!")


get_settings.cache_clear()


@pytest.fixture(scope="session")
def engine():
    e = create_engine(_TEST_DB_URL, pool_pre_ping=True)
    with e.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=e)
    with e.connect() as conn:
        conn.execute(
            text("ALTER TABLE notes ADD COLUMN IF NOT EXISTS embedding vector(1536)")
        )
        conn.commit()
    yield e
    Base.metadata.drop_all(bind=e)


@pytest.fixture
def db(engine):
    with engine.connect() as conn:
        trans = conn.begin()
        session = Session(conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            trans.rollback()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db_user(db):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"tuser_{uid}",
        email=f"tuser_{uid}@example.com",
        hashed_password=hash_password("TestPass123!"),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return user, "TestPass123!"


@pytest.fixture
def auth_client(client, db_user):
    user, _ = db_user
    token = create_access_token(user.id)
    client.cookies.set("access_token", token)
    return client, user


@pytest.fixture
def db_note(db, db_user):
    user, _ = db_user
    note = Note(user_id=user.id, description="Integration test note")
    db.add(note)
    db.flush()
    return note


@pytest.fixture
def db_task(db, db_user, db_note):
    user, _ = db_user
    task = NoteTask(
        note_id=db_note.id,
        user_id=user.id,
        title="Test task",
        status="local",
        source="manual",
    )
    db.add(task)
    db.flush()
    return task


@pytest.fixture
def db_label(db, db_user):
    from app.models import Label

    user, _ = db_user
    label = Label(user_id=user.id, title="Test Label", color="#aabbcc")
    db.add(label)
    db.flush()
    return label


@pytest.fixture
def db_llm_config(db, db_user):
    from app.models import UserLLMConfig
    from app.auth.utils import encrypt_value

    user, _ = db_user
    config = UserLLMConfig(
        user_id=user.id,
        provider_name="openai",
        model_name="gpt-4o-mini",
        api_key_encrypted=encrypt_value("sk-fake-key"),
        is_active=True,
    )
    db.add(config)
    db.flush()
    return config


@pytest.fixture
def db_discovered_task(db, db_user, db_note):
    from app.models import NoteTask

    user, _ = db_user
    task = NoteTask(
        note_id=db_note.id,
        user_id=user.id,
        title="Discovered task",
        status="discovered",
        source="nlp",
    )
    db.add(task)
    db.flush()
    return task
