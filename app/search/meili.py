from __future__ import annotations

import meilisearch

from app.config import get_settings

_INDEX = "notes"
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
        client.index(_INDEX).update_filterable_attributes(["user_id"])
        client.index(_INDEX).update_searchable_attributes(["description"])
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


def search(query: str, user_id: str, limit: int = 50) -> list[str]:
    client = _get_client()
    if not client:
        return []
    try:
        result = client.index(_INDEX).search(
            query,
            {
                "filter": f'user_id = "{user_id}"',
                "limit": limit,
            },
        )
        return [hit["id"] for hit in result["hits"]]
    except Exception:
        return []
