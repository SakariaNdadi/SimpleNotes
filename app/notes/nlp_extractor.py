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

# Sentence boundary split for regex-only fallback
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


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


def _dates_in_sent(sent) -> str | None:
    """Extract first resolvable date/time from spaCy NER entities in the sentence."""
    for ent in sent.ents:
        if ent.label_ in ("DATE", "TIME"):
            result = _parse_date(ent.text)
            if result:
                return result
    return None


def _dates_in_text(text: str) -> str | None:
    """Extract first resolvable date/time phrase from free text via sliding word-window scan."""
    import dateparser

    result = dateparser.parse(
        text,
        settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    if result:
        return result.strftime("%Y-%m-%dT%H:%M")
    words = text.split()
    for size in range(4, 0, -1):
        for i in range(len(words) - size + 1):
            chunk = " ".join(words[i : i + size])
            r = dateparser.parse(
                chunk,
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
            if r:
                return r.strftime("%Y-%m-%dT%H:%M")
    return None


def _process_chunk(
    chunk: str,
    inherited_action: str | None,
    seen: set[str],
    date_str: str | None = None,
) -> dict | None:
    """Convert a text chunk into a task dict, or None if not actionable."""
    chunk = chunk.strip()
    if not chunk or len(chunk) < 4:
        return None

    has_trigger = bool(_TRIGGER.search(chunk))

    if not date_str:
        date_str = _parse_date(chunk) if (has_trigger or inherited_action) else None

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
    if nlp is not None:
        return _extract_with_spacy(nlp, text)
    return _extract_regex_only(text)


def _extract_with_spacy(nlp, text: str) -> list[dict]:
    doc = nlp(text[:4000])
    tasks: list[dict] = []
    seen: set[str] = set()

    for sent in doc.sents:
        raw = sent.text.strip()
        if not raw:
            continue

        has_trigger = bool(_TRIGGER.search(raw))
        has_date_ent = any(e.label_ in ("DATE", "TIME") for e in sent.ents)

        if not has_trigger and not has_date_ent:
            continue

        # Resolve date once per sentence from NER — avoids O(n²) dateparser scan
        sent_date = _dates_in_sent(sent)

        chunks = _COMPOUND_SPLIT.split(raw)

        inherited_action: str | None = None
        m = _ACTION_NOUN.search(chunks[0])
        if m:
            inherited_action = m.group(1)

        for i, chunk in enumerate(chunks):
            action = None if i == 0 else inherited_action
            task = _process_chunk(chunk, action, seen, date_str=sent_date)
            if task:
                tasks.append(task)

        if len(tasks) >= 5:
            break

    return tasks[:5]


def _extract_regex_only(text: str) -> list[dict]:
    """Fallback extraction without spaCy: sentence-split on punctuation, match triggers."""
    sentences = _SENT_SPLIT.split(text[:4000])
    tasks: list[dict] = []
    seen: set[str] = set()

    for raw in sentences:
        raw = raw.strip()
        if not raw or not _TRIGGER.search(raw):
            continue

        chunks = _COMPOUND_SPLIT.split(raw)

        inherited_action: str | None = None
        m = _ACTION_NOUN.search(chunks[0])
        if m:
            inherited_action = m.group(1)

        for i, chunk in enumerate(chunks):
            action = None if i == 0 else inherited_action
            task = _process_chunk(chunk, action, seen)
            if task:
                tasks.append(task)

        if len(tasks) >= 5:
            break

    return tasks[:5]


def _is_event(text: str) -> bool:
    return bool(
        re.search(r"\b(meeting|appointment|call with|schedule)\b", text, re.IGNORECASE)
    )
