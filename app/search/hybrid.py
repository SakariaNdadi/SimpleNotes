from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Note


async def hybrid_search(
    db: Session, user_id: str, query: str, limit: int = 50
) -> list[Note]:
    from app.search.embeddings import get_embedding
    from app.search.meili import search as meili_search

    settings = get_settings()
    is_postgres = not settings.DATABASE_URL.startswith("sqlite")

    meili_ids = meili_search(query, user_id, limit)

    if is_postgres and settings.EMBEDDING_MODEL:
        from app.search.vector import similarity_search

        embedding = await get_embedding(query)
        if embedding:
            vector_ids = similarity_search(db, user_id, embedding, limit)
            seen: set[str] = set()
            merged: list[str] = []
            for nid in vector_ids + meili_ids:
                if nid not in seen:
                    seen.add(nid)
                    merged.append(nid)
            result_ids = merged[:limit]
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

    index_note(note_id, user_id, description)

    settings = get_settings()
    if not settings.EMBEDDING_MODEL or settings.DATABASE_URL.startswith("sqlite"):
        return

    embedding = await get_embedding(description)
    if not embedding:
        return

    from app.search.vector import store_embedding

    db = SessionLocal()
    try:
        store_embedding(db, note_id, embedding)
    finally:
        db.close()
