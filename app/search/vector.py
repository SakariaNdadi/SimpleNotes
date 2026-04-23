from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(v) for v in embedding) + "]"


def store_embedding(db: Session, note_id: str, embedding: list[float]) -> None:
    db.execute(
        text("UPDATE notes SET embedding = CAST(:emb AS vector) WHERE id = :id"),
        {"emb": _format_vector(embedding), "id": note_id},
    )


def similarity_search(
    db: Session, user_id: str, embedding: list[float], limit: int = 50
) -> list[str]:
    rows = db.execute(
        text("""
            SELECT id FROM notes
            WHERE user_id = :user_id
              AND is_deleted = false
              AND is_archived = false
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :limit
        """),
        {"user_id": user_id, "emb": _format_vector(embedding), "limit": limit},
    ).fetchall()
    return [r[0] for r in rows]
