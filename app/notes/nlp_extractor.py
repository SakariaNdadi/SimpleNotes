from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spacy

_nlp = None

_TRIGGER = re.compile(
    r"\b(need to|have to|should|must|remember to|don'?t forget|remind me|"
    r"schedule|meeting|call with|pick up|buy|send|submit|deadline|appointment|"
    r"due|follow up|check in|review|finish|complete|prepare|book|register|"
    r"watch|attend|join|visit|go to|see|catch|play|run|exercise|gym|dinner|"
    r"lunch|breakfast|coffee|flight|train|drive|pick|drop)\b",
    re.IGNORECASE,
)

_STRIP_LEAD = re.compile(
    r"^(i (need|have) to|i should|remember to|don'?t forget to|remind me to)\s+",
    re.IGNORECASE,
)


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy as _spacy
            _nlp = _spacy.load("en_core_web_sm")
        except Exception:
            _nlp = False
    return _nlp if _nlp else None


def extract_tasks(text: str) -> list[dict]:
    nlp = _get_nlp()
    if nlp is None:
        return []

    import dateparser

    doc = nlp(text[:4000])
    tasks: list[dict] = []
    seen: set[str] = set()

    for sent in doc.sents:
        raw = sent.text.strip()
        has_trigger = bool(_TRIGGER.search(raw))

        date_str: str | None = None
        for ent in sent.ents:
            if ent.label_ in ("DATE", "TIME"):
                parsed = dateparser.parse(
                    ent.text,
                    settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
                )
                if parsed:
                    date_str = parsed.strftime("%Y-%m-%dT%H:%M")
                    break

        # Skip if no trigger AND no date entity
        if not raw or (not has_trigger and not date_str):
            continue

        title = _STRIP_LEAD.sub("", raw).rstrip(".,;!").strip()
        if not title or len(title) < 5:
            continue
        if len(title) > 120:
            title = title[:120] + "…"

        key = title.lower()
        if key in seen:
            continue
        seen.add(key)

        task_type = "event" if _is_event(raw) else "task"
        tasks.append({
            "title": title,
            "description": "",
            "datetime": date_str,
            "type": task_type,
        })

    return tasks[:5]


def _is_event(text: str) -> bool:
    return bool(re.search(r"\b(meeting|appointment|call with|schedule)\b", text, re.IGNORECASE))
