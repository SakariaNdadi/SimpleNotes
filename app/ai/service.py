"""
AI service using LiteLLM.

Supports:
- Cloud providers: OpenAI, Anthropic, Gemini, etc. (via api_key)
- Self-hosted: Ollama, llama.cpp, vLLM, DeepSeek, Gemma (via base_url)
- Any OpenAI-compatible endpoint (base_url + model)

If LiteLLM doesn't support a custom endpoint, falls back to direct httpx call.
"""

from __future__ import annotations

from app.auth.utils import decrypt_value
from app.models import UserLLMConfig

import json
import logging
import re
from datetime import date, datetime

import httpx
import litellm
from sqlalchemy.orm import Session

litellm.suppress_debug_info = True
for _log in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    logging.getLogger(_log).setLevel(logging.CRITICAL)
logging.getLogger("vertex_llm_base").setLevel(logging.CRITICAL)


def _relative_date_label(note_dt: datetime | None, today: date) -> str:
    if note_dt is None:
        return "unknown date"
    note_date = note_dt.date()
    delta = (today - note_date).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "yesterday"
    if delta < 7:
        return f"{delta} days ago"
    if delta < 14:
        return "last week"
    if today.year == note_date.year and today.month == note_date.month:
        return f"this month on the {note_date.day}"
    if delta <= 60:
        return f"last month on the {note_date.day}"
    if today.year == note_date.year:
        return f"{note_date.strftime('%b')} {note_date.day}"
    return note_date.strftime("%b %d, %Y")


def _get_active_config(db: Session, user_id: str) -> UserLLMConfig | None:
    return (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == user_id, UserLLMConfig.is_active)
        .order_by(UserLLMConfig.created_at.desc())
        .first()
    )


def _build_litellm_kwargs(config: UserLLMConfig) -> dict:
    kwargs: dict = {"model": config.model_name.strip()}
    if config.api_key_encrypted:
        key = decrypt_value(config.api_key_encrypted)
        if key:
            kwargs["api_key"] = key
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return kwargs


async def _fallback_openai_compat(
    base_url: str, model: str, api_key: str | None, messages: list
) -> str:
    """Direct httpx call for OpenAI-compatible endpoints LiteLLM may not handle."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model, "messages": messages}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/v1/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def complete(db: Session, user_id: str, messages: list[dict]) -> str:
    config = _get_active_config(db, user_id)
    if not config:
        return "No LLM configured. Go to Settings → AI to add one."

    kwargs = _build_litellm_kwargs(config)
    try:
        response = await litellm.acompletion(messages=messages, **kwargs)
        return response.choices[0].message.content or ""
    except Exception as litellm_err:
        if config.base_url:
            try:
                api_key = (
                    decrypt_value(config.api_key_encrypted) or None
                    if config.api_key_encrypted
                    else None
                )
                return await _fallback_openai_compat(
                    config.base_url, config.model_name, api_key, messages
                )
            except Exception:
                pass
        err_str = str(litellm_err)
        if "DefaultCredentialsError" in err_str and "api_key" not in kwargs:
            return "LLM credentials not set. Go to Settings → AI and add an API key for your provider."
        return f"AI error: {litellm_err}"


async def summarize_note(
    db: Session, user_id: str, note_text: str, languages: list[str] | None = None
) -> str:
    lang_hint = ""
    if languages and languages != ["en"]:
        lang_hint = f" The user writes in: {', '.join(languages)}. Preserve language context in your summary."
    messages = [
        {
            "role": "system",
            "content": f"Summarize the following note in 2-3 concise sentences.{lang_hint}",
        },
        {"role": "user", "content": note_text},
    ]
    return await complete(db, user_id, messages)


async def detect_tasks(db: Session, user_id: str, note_text: str) -> list[dict]:
    """
    Returns list of detected tasks/reminders:
    [{"title": "...", "description": "...", "type": "task|reminder", "datetime": "ISO or null"}]
    """
    messages = [
        {
            "role": "system",
            "content": (
                "Extract any tasks, todos, or reminders from the note. "
                'Return JSON array: [{"title": str, "description": str, "type": "task|reminder", "datetime": "ISO8601 or null"}]. '
                "Return empty array [] if none found. Return ONLY valid JSON."
            ),
        },
        {"role": "user", "content": note_text},
    ]
    raw = await complete(db, user_id, messages)
    try:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        return json.loads(match.group()) if match else []
    except (json.JSONDecodeError, ValueError):
        return []


async def answer_from_notes(
    db: Session, user_id: str, query: str, notes: list, today: date | None = None
) -> str:
    if not notes:
        return ""
    if today is None:
        today = date.today()
    context = "\n".join(
        f"[{i + 1}] ({_relative_date_label(n.created_at, today)}): {n.description[:300]}"
        for i, n in enumerate(notes)
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a personal notes assistant. Today's date is {today.strftime('%A, %B %d, %Y')}. "
                "When the user asks about 'tomorrow', 'today', 'next week', or other relative time references, "
                f"interpret them relative to today ({today}). "
                "Answer the user's question directly and concisely using only the notes provided as context. "
                "When referencing a note, use its relative date label (e.g., 'last month on the 12th you noted...'). "
                "If the notes don't contain enough information, say so briefly."
            ),
        },
        {"role": "user", "content": f"Question: {query}\n\nNotes:\n{context}"},
    ]
    return await complete(db, user_id, messages)


async def semantic_search(
    db: Session,
    user_id: str,
    query: str,
    notes: list,
    languages: list[str] | None = None,
    today: date | None = None,
) -> list:
    """
    Dev fallback: rank notes by keyword relevance using LLM.
    Prod should use pgvector embeddings instead.
    """
    if not notes:
        return []

    if today is None:
        today = date.today()

    lang_hint = ""
    if languages:
        lang_hint = f" The user may write notes in: {', '.join(languages)}. Consider multilingual matches."

    numbered = "\n".join(
        f"{i + 1}. ({_relative_date_label(n.created_at, today)}) {n.description[:200]}"
        for i, n in enumerate(notes)
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"Today is {today.strftime('%A, %B %d, %Y')}. "
                "Interpret temporal references in the query (tomorrow, today, next week, last month, etc.) relative to today. "
                "Given the search query and a numbered list of notes with their relative dates, "
                "return the numbers of the most relevant notes in order of relevance as a JSON array of integers. "
                f"Max 10 results. Return ONLY JSON array.{lang_hint}"
            ),
        },
        {"role": "user", "content": f"Query: {query}\n\nNotes:\n{numbered}"},
    ]
    raw = await complete(db, user_id, messages)
    try:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        indices = json.loads(match.group()) if match else []
        results = [notes[i - 1] for i in indices if 1 <= i <= len(notes)]
        return results if results else notes[:10]
    except (json.JSONDecodeError, ValueError, IndexError):
        return notes[:10]
