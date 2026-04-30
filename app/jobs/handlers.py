import logging
from collections.abc import Callable

from app.jobs.schemas import (
    AiDetectTasksPayload,
    EmbedAndIndexPayload,
    NlpDiscoverPayload,
)

_log = logging.getLogger(__name__)


async def handle_embed_and_index(payload: dict) -> None:
    from app.search.hybrid import embed_and_index

    p = EmbedAndIndexPayload(**payload)
    await embed_and_index(p.note_id, p.user_id, p.description)


async def handle_nlp_discover(payload: dict) -> None:
    from app.database import SessionLocal
    from app.notes.nlp_extractor import extract_tasks
    from app.notes.task_service import save_tasks

    p = NlpDiscoverPayload(**payload)
    db = SessionLocal()
    try:
        tasks = extract_tasks(p.text)
        if tasks:
            save_tasks(
                db, p.user_id, p.note_id, tasks, source="nlp", status="discovered"
            )
    except Exception:
        _log.exception("nlp_discover failed for note %s", p.note_id)
    finally:
        db.close()


async def handle_ai_detect_tasks(payload: dict) -> None:
    from app.ai.service import detect_tasks
    from app.database import SessionLocal
    from app.notes.task_service import save_tasks

    p = AiDetectTasksPayload(**payload)
    db = SessionLocal()
    try:
        raw_tasks = await detect_tasks(db, p.user_id, p.note_text)
        tasks = [t for t in raw_tasks if isinstance(t, dict)]
        if tasks:
            save_tasks(
                db, p.user_id, p.note_id, tasks, source="llm", status="discovered"
            )
    except Exception:
        _log.exception("ai_detect_tasks failed for note %s", p.note_id)
    finally:
        db.close()


HANDLERS: dict[str, Callable] = {
    "embed_and_index": handle_embed_and_index,
    "nlp_discover": handle_nlp_discover,
    "ai_detect_tasks": handle_ai_detect_tasks,
}
