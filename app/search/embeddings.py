from __future__ import annotations

import litellm

from app.config import get_settings


async def get_embedding(text: str) -> list[float] | None:
    model = get_settings().EMBEDDING_MODEL
    if not model:
        return None
    try:
        resp = await litellm.aembedding(model=model, input=[text[:8000]])
        return resp.data[0]["embedding"]
    except Exception:
        return None
