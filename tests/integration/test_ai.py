"""
Integration tests for app/ai/router.py.

ISTQB techniques: EP, Decision Table, Error Guessing.
LiteLLM calls are patched with AsyncMock to avoid real network calls.
"""

import uuid
from unittest.mock import AsyncMock, patch


from app.models import NoteSummary, UserLLMConfig
from app.notes.summary_service import save_summary


# ── LLM Config CRUD ───────────────────────────────────────────────────────────


def test_get_llm_settings_page(auth_client):
    """EP: settings page accessible when authenticated."""
    client, _ = auth_client
    r = client.get("/settings/llm")
    assert r.status_code == 200


def test_post_llm_config_saves_and_sets_active(auth_client, db):
    """EP: POST creates a config record with is_active=True."""
    client, user = auth_client
    r = client.post(
        "/settings/llm",
        data={
            "provider_name": "openai",
            "model_name": "gpt-4o",
            "base_url": "",
            "api_key": "sk-test-key",
        },
    )
    assert r.status_code == 200
    config = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == user.id, UserLLMConfig.model_name == "gpt-4o")
        .first()
    )
    assert config is not None
    assert config.is_active is True


def test_post_llm_config_deactivates_previous(auth_client, db, db_llm_config):
    """Decision Table: adding a new config deactivates all previous ones."""
    client, user = auth_client
    client.post(
        "/settings/llm",
        data={
            "provider_name": "anthropic",
            "model_name": "claude-3-haiku",
            "base_url": "",
            "api_key": "sk-ant-key",
        },
    )
    db.refresh(db_llm_config)
    assert db_llm_config.is_active is False


def test_delete_llm_config(auth_client, db, db_llm_config):
    """EP: DELETE removes the config from DB."""
    client, _ = auth_client
    r = client.delete(f"/settings/llm/{db_llm_config.id}")
    assert r.status_code == 200
    found = db.query(UserLLMConfig).filter(UserLLMConfig.id == db_llm_config.id).first()
    assert found is None


def test_get_llm_edit_form(auth_client, db_llm_config):
    """EP: edit form endpoint returns 200 with config data."""
    client, _ = auth_client
    r = client.get(f"/settings/llm/{db_llm_config.id}/edit")
    assert r.status_code == 200


def test_get_llm_edit_form_not_found(auth_client):
    """EG: non-existent config id → 404."""
    client, _ = auth_client
    r = client.get(f"/settings/llm/{uuid.uuid4()}/edit")
    assert r.status_code == 404


def test_put_llm_config_updates_model_name(auth_client, db, db_llm_config):
    """EP: PUT updates the model_name field in DB."""
    client, _ = auth_client
    r = client.put(
        f"/settings/llm/{db_llm_config.id}",
        data={
            "provider_name": "openai",
            "model_name": "gpt-4-turbo",
            "base_url": "",
            "api_key": "",
        },
    )
    assert r.status_code == 200
    db.refresh(db_llm_config)
    assert db_llm_config.model_name == "gpt-4-turbo"


def test_post_llm_deactivate(auth_client, db, db_llm_config):
    """EP: deactivate sets is_active=False."""
    client, _ = auth_client
    r = client.post(f"/settings/llm/{db_llm_config.id}/deactivate")
    assert r.status_code == 200
    db.refresh(db_llm_config)
    assert db_llm_config.is_active is False


def test_post_llm_activate_deactivates_others(auth_client, db, db_llm_config):
    """Decision Table: activating one config deactivates all others for that user."""
    client, user = auth_client
    # Create a second config
    second = UserLLMConfig(
        user_id=user.id,
        provider_name="anthropic",
        model_name="claude-3-opus",
        is_active=True,
    )
    db.add(second)
    db.flush()

    # Activate db_llm_config → second should become inactive
    r = client.post(f"/settings/llm/{db_llm_config.id}/activate")
    assert r.status_code == 200
    db.refresh(db_llm_config)
    db.refresh(second)
    assert db_llm_config.is_active is True
    assert second.is_active is False


# ── AI Summary ────────────────────────────────────────────────────────────────


def test_summarize_note_no_llm_config(client, db, db_note, db_user):
    """EG: no LLM config → response contains 'No LLM configured'."""
    user, password = db_user
    from app.auth.utils import create_access_token

    token = create_access_token(user.id)
    client.cookies.set("access_token", token)
    r = client.post(f"/ai/summary/{db_note.id}")
    assert r.status_code == 200
    assert "No LLM configured" in r.text


def test_summarize_note_calls_ai_when_save_disabled(
    auth_client, db, db_note, db_llm_config
):
    """EP: with save_ai_summaries=False, AI is called and result returned."""
    client, user = auth_client
    from app.preferences.service import get_or_create_prefs

    prefs = get_or_create_prefs(db, user.id)
    prefs.save_ai_summaries = False
    db.flush()

    with patch("app.ai.service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = "Mocked AI summary text"
        r = client.post(f"/ai/summary/{db_note.id}")

    assert r.status_code == 200
    assert "Mocked AI summary text" in r.text


def test_summarize_note_returns_cached_summary(auth_client, db, db_note, db_llm_config):
    """EP: with save_ai_summaries=True and existing cache, returns cached content."""
    client, user = auth_client
    from app.preferences.service import get_or_create_prefs

    prefs = get_or_create_prefs(db, user.id)
    prefs.save_ai_summaries = True
    db.flush()

    save_summary(db, db_note.id, user.id, "Cached summary content")

    with patch("app.ai.service.complete", new_callable=AsyncMock) as mock_complete:
        r = client.post(f"/ai/summary/{db_note.id}")
        mock_complete.assert_not_called()

    assert r.status_code == 200
    assert "Cached summary content" in r.text


def test_delete_summary(auth_client, db, db_note):
    """EP: DELETE removes the NoteSummary record."""
    client, user = auth_client
    save_summary(db, db_note.id, user.id, "Summary to delete")

    r = client.delete(f"/ai/summary/{db_note.id}")
    assert r.status_code == 200

    found = (
        db.query(NoteSummary)
        .filter(NoteSummary.note_id == db_note.id, NoteSummary.user_id == user.id)
        .first()
    )
    assert found is None


# ── AI Search ─────────────────────────────────────────────────────────────────


def test_ai_search_returns_200(auth_client):
    """EP: POST /ai/search returns 200."""
    client, _ = auth_client
    with (
        patch("app.ai.service.complete", new_callable=AsyncMock) as mock_complete,
        patch("app.search.hybrid.hybrid_search", new_callable=AsyncMock) as mock_hybrid,
    ):
        mock_complete.return_value = "[]"
        mock_hybrid.return_value = []
        r = client.post("/ai/search", data={"query": "test query"})
    assert r.status_code == 200


def test_ai_search_unauthenticated(client):
    """EG: unauthenticated request → 401."""
    r = client.post("/ai/search", data={"query": "test"})
    assert r.status_code == 401


# ── AI Detect Tasks ───────────────────────────────────────────────────────────


def test_detect_tasks_returns_200(auth_client, db_note):
    """EP: POST /ai/detect-tasks returns 200."""
    client, _ = auth_client
    with patch("app.ai.service.detect_tasks", new_callable=AsyncMock) as mock_detect:
        mock_detect.return_value = []
        r = client.post(f"/ai/detect-tasks/{db_note.id}")
    assert r.status_code == 200


def test_detect_tasks_nonexistent_note_returns_200_empty(auth_client):
    """EG: note not found → 200 with empty body."""
    client, _ = auth_client
    r = client.post(f"/ai/detect-tasks/{uuid.uuid4()}")
    assert r.status_code == 200
    assert r.text.strip() == ""


def test_detect_tasks_unauthenticated(client, db_note):
    """EG: unauthenticated request → 401."""
    r = client.post(f"/ai/detect-tasks/{db_note.id}")
    assert r.status_code == 401
