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

import httpx
import litellm
from sqlalchemy.orm import Session

litellm.suppress_debug_info = True
for _log in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    logging.getLogger(_log).setLevel(logging.CRITICAL)
logging.getLogger("vertex_llm_base").setLevel(logging.CRITICAL)


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
        start = raw.find("[")
        end = raw.rfind("]") + 1
        return json.loads(raw[start:end]) if start != -1 else []
    except (json.JSONDecodeError, ValueError):
        return []


async def answer_from_notes(db: Session, user_id: str, query: str, notes: list) -> str:
    if not notes:
        return ""
    context = "\n".join(
        f"[{i + 1}] ({n.created_at.strftime('%b %d, %Y') if n.created_at else '?'}): {n.description[:300]}"
        for i, n in enumerate(notes)
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a personal notes assistant. Answer the user's question directly and concisely "
                "using only the notes provided as context. Include relevant dates or details from the notes. "
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
) -> list:
    """
    Dev fallback: rank notes by keyword relevance using LLM.
    Prod should use pgvector embeddings instead.
    """
    if not notes:
        return []

    lang_hint = ""
    if languages:
        lang_hint = f" The user may write notes in: {', '.join(languages)}. Consider multilingual matches."

    numbered = "\n".join(f"{i + 1}. {n.description[:200]}" for i, n in enumerate(notes))
    messages = [
        {
            "role": "system",
            "content": (
                "Given the search query and a numbered list of notes, return the numbers of the most relevant notes "
                f"in order of relevance as a JSON array of integers. Max 10 results. Return ONLY JSON array.{lang_hint}"
            ),
        },
        {"role": "user", "content": f"Query: {query}\n\nNotes:\n{numbered}"},
    ]
    raw = await complete(db, user_id, messages)
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        indices = json.loads(raw[start:end]) if start != -1 else []
        results = [notes[i - 1] for i in indices if 1 <= i <= len(notes)]
        return results if results else notes[:10]
    except (json.JSONDecodeError, ValueError, IndexError):
        return notes[:10]
