from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

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

# Splits compound tasks: "schedule X and then Y", "X then Y", "X, and Y"
_COMPOUND_SPLIT = re.compile(
    r"\s+(?:and then|and also|then|and afterwards|, and)\s+",
    re.IGNORECASE,
)

# Detects continuation phrases like "one with X", "another with X"
_CONTINUATION = re.compile(r"^(one|another)\b", re.IGNORECASE)

# Extracts the action noun right after a trigger (e.g., "schedule a meeting" → "meeting")
_ACTION_NOUN = re.compile(
    r"\b(?:schedule|have|book|arrange|set up)\s+(?:a\s+|an\s+)?(\w+)",
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


def _parse_date(text: str) -> str | None:
    import dateparser
    parsed = dateparser.parse(
        text,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    return parsed.strftime("%Y-%m-%dT%H:%M") if parsed else None


def _dates_in_text(text: str) -> str | None:
    """Extract first resolvable date/time phrase from free text via dateparser."""
    import dateparser
    # Try whole chunk first
    result = dateparser.parse(
        text,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    # dateparser on a long sentence often fails — fall back to word-window scan
    if result:
        return result.strftime("%Y-%m-%dT%H:%M")
    # Slide a window of 1-4 words to find date phrases
    words = text.split()
    for size in range(4, 0, -1):
        for i in range(len(words) - size + 1):
            chunk = " ".join(words[i : i + size])
            r = dateparser.parse(
                chunk,
                settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
            )
            if r:
                return r.strftime("%Y-%m-%dT%H:%M")
    return None


def _process_chunk(chunk: str, inherited_action: str | None, seen: set[str]) -> dict | None:
    """Convert a text chunk into a task dict, or None if not actionable."""
    chunk = chunk.strip()
    if not chunk or len(chunk) < 4:
        return None

    has_trigger = bool(_TRIGGER.search(chunk))

    # Resolve date from spaCy ents isn't available here — use word-scan
    date_str = _dates_in_text(chunk)

    if not has_trigger and not date_str and not inherited_action:
        return None

    # Reconstruct continuation phrases: "one with X" → "<action> with X"
    title = chunk
    if inherited_action and _CONTINUATION.match(chunk):
        title = _CONTINUATION.sub(inherited_action, chunk, count=1)

    title = _STRIP_LEAD.sub("", title).rstrip(".,;!").strip()
    if not title or len(title) < 5:
        return None
    if len(title) > 120:
        title = title[:120] + "…"

    key = title.lower()
    if key in seen:
        return None
    seen.add(key)

    task_type = "event" if _is_event(chunk) else "task"
    return {"title": title, "description": "", "datetime": date_str, "type": task_type}


def extract_tasks(text: str) -> list[dict]:
    nlp = _get_nlp()
    if nlp is None:
        return []

    doc = nlp(text[:4000])
    tasks: list[dict] = []
    seen: set[str] = set()

    for sent in doc.sents:
        raw = sent.text.strip()
        if not raw:
            continue

        # Check if this sentence is worth processing at all
        has_trigger = bool(_TRIGGER.search(raw))
        # Quick date check using spaCy NER
        has_date_ent = any(e.label_ in ("DATE", "TIME") for e in sent.ents)

        if not has_trigger and not has_date_ent:
            continue

        # Split compound sentence into individual task chunks
        chunks = _COMPOUND_SPLIT.split(raw)

        # Extract action noun from first chunk for continuation reconstruction
        inherited_action: str | None = None
        m = _ACTION_NOUN.search(chunks[0])
        if m:
            inherited_action = m.group(1)  # e.g. "meeting"

        for i, chunk in enumerate(chunks):
            action = None if i == 0 else inherited_action
            task = _process_chunk(chunk, action, seen)
            if task:
                tasks.append(task)

        if len(tasks) >= 5:
            break

    return tasks[:5]


def _is_event(text: str) -> bool:
    return bool(re.search(r"\b(meeting|appointment|call with|schedule)\b", text, re.IGNORECASE))
