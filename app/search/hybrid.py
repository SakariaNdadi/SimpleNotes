from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Note

_log = logging.getLogger(__name__)


def _rrf_merge(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda doc_id: scores[doc_id], reverse=True)


async def hybrid_search(
    db: Session, user_id: str, query: str, limit: int = 50
) -> list[Note]:
    from app.search.embeddings import get_embedding
    from app.search.meili import search as meili_search

    settings = get_settings()

    meili_ids = await asyncio.to_thread(meili_search, query, user_id, limit)

    if settings.is_postgres and settings.EMBEDDING_MODEL:
        from app.search.vector import similarity_search

        embedding = await get_embedding(query)
        if embedding:
            vector_ids = await asyncio.to_thread(
                similarity_search, db, user_id, embedding, limit
            )
            result_ids = _rrf_merge([vector_ids, meili_ids])[:limit]
        else:
            result_ids = meili_ids
    else:
        result_ids = meili_ids

    if not result_ids:
        from app.notes.service import search_notes

        return search_notes(db, user_id, query)

    notes_by_id = {
        n.id: n
        for n in db.query(Note)
        .filter(
            Note.id.in_(result_ids),
            Note.user_id == user_id,
            Note.is_deleted == False,  # noqa: E712
            Note.is_archived == False,  # noqa: E712
        )
        .all()
    }
    return [notes_by_id[nid] for nid in result_ids if nid in notes_by_id]


async def embed_and_index(note_id: str, user_id: str, description: str) -> None:
    from app.search.embeddings import get_embedding
    from app.search.meili import index_note
    from app.config import get_settings
    from app.database import SessionLocal

    try:
        await asyncio.to_thread(index_note, note_id, user_id, description)
    except Exception:
        _log.exception("Meilisearch indexing failed for note %s", note_id)

    settings = get_settings()
    if not settings.EMBEDDING_MODEL or not settings.is_postgres:
        return

    embedding = await get_embedding(description)
    if not embedding:
        return

    from app.search.vector import store_embedding

    db = SessionLocal()
    try:
        store_embedding(db, note_id, embedding)
        db.commit()
    except Exception:
        _log.exception("Vector store failed for note %s", note_id)
        db.rollback()
    finally:
        db.close()
