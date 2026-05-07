from __future__ import annotations

import meilisearch

from app.config import get_settings

_INDEX = "notes"
_SUPPORTED_LOCALES = ["en", "fr", "es", "de", "ar", "zh", "pt", "it", "ja", "ko"]
_client_instance: meilisearch.Client | None = None


def _get_client() -> meilisearch.Client | None:
    global _client_instance
    if _client_instance is None:
        s = get_settings()
        if not s.MEILI_URL:
            return None
        _client_instance = meilisearch.Client(s.MEILI_URL, s.MEILI_KEY or None)
    return _client_instance


def setup_index() -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.create_index(_INDEX, {"primaryKey": "id"})
        client.index(_INDEX).update_settings(
            {
                "filterableAttributes": ["user_id"],
                "searchableAttributes": ["description"],
                "typoTolerance": {
                    "enabled": True,
                    "minWordSizeForTypos": {
                        "oneTypo": 4,
                        "twoTypos": 7,
                    },
                },
                "localizedAttributes": [
                    {
                        "locales": _SUPPORTED_LOCALES,
                        "attributePatterns": ["description"],
                    }
                ],
            }
        )
    except Exception:
        pass


def index_note(note_id: str, user_id: str, description: str) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.index(_INDEX).add_documents(
            [
                {
                    "id": note_id,
                    "user_id": user_id,
                    "description": description,
                }
            ]
        )
    except Exception:
        pass


def delete_note(note_id: str) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.index(_INDEX).delete_document(note_id)
    except Exception:
        pass


def search(
    query: str, user_id: str, limit: int = 50, locales: list[str] | None = None
) -> list[str]:
    client = _get_client()
    if not client:
        return []
    try:
        params: dict = {
            "filter": f'user_id = "{user_id}"',
            "limit": limit,
        }
        if locales:
            params["locales"] = locales
        result = client.index(_INDEX).search(query, params)
        return [hit["id"] for hit in result["hits"]]
    except Exception:
        return []
