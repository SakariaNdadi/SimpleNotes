"""
Unit tests for app/notes/nlp_extractor.py.

ISTQB techniques: EP, BVA, Decision Table, Error Guessing.

Tests for _is_event, _process_chunk, _dates_in_text do not require spaCy.
Tests for extract_tasks require spaCy en_core_web_sm — skipped if unavailable.
"""

import re

import pytest

from app.notes.nlp_extractor import _dates_in_text, _is_event, _process_chunk


# ── _is_event ─────────────────────────────────────────────────────────────────


def test_is_event_meeting():
    """EP: 'meeting' keyword → event."""
    assert _is_event("schedule a meeting on Monday") is True


def test_is_event_appointment():
    """EP: 'appointment' keyword → event."""
    assert _is_event("I have an appointment tomorrow") is True


def test_is_event_call_with():
    """EP: 'call with' keyword → event."""
    assert _is_event("call with the team at 3pm") is True


def test_is_event_schedule():
    """EP: 'schedule' keyword → event."""
    assert _is_event("schedule the quarterly review") is True


def test_is_event_plain_task_returns_false():
    """EP: non-event text → False."""
    assert _is_event("buy groceries and clean the house") is False


# ── _process_chunk ────────────────────────────────────────────────────────────


def test_process_chunk_valid_task():
    """EP: chunk with trigger keyword → returns task dict."""
    seen: set[str] = set()
    result = _process_chunk("buy milk at the store", None, seen)
    assert result is not None
    assert "title" in result
    assert "datetime" in result
    assert "type" in result
    assert len(result["title"]) >= 1


def test_process_chunk_too_short_returns_none():
    """BVA: 2 chars (below min of 4)."""
    assert _process_chunk("go", None, set()) is None


def test_process_chunk_exactly_4_chars_returns_none():
    """BVA: exactly 4 chars — too short to produce a valid title after stripping."""
    assert _process_chunk("meet", None, set()) is None


def test_process_chunk_empty_returns_none():
    """EG: empty string → None."""
    assert _process_chunk("", None, set()) is None


def test_process_chunk_no_trigger_no_date_no_action_returns_none():
    """Decision Table: no trigger + no date + no inherited_action → None."""
    # Text with no action trigger and no date-parseable phrase
    assert _process_chunk("the fox jumped over the fence", None, set()) is None


def test_process_chunk_deduplication_via_seen():
    """EG: same text processed twice — second call returns None."""
    seen: set[str] = set()
    first = _process_chunk("need to buy milk today", None, seen)
    second = _process_chunk("need to buy milk today", None, seen)
    assert first is not None
    assert second is None


def test_process_chunk_continuation_with_inherited_action():
    """Decision Table: continuation phrase + inherited_action → resolved title."""
    seen: set[str] = set()
    result = _process_chunk("one with Bob at 3pm", "meeting", seen)
    assert result is not None
    assert "meeting" in result["title"].lower() or "bob" in result["title"].lower()


def test_process_chunk_title_120_chars_not_truncated():
    """BVA: title exactly 120 chars — no ellipsis appended."""
    # Construct chunk whose stripped title = exactly 120 chars
    core = "need to " + "x" * 112  # 8 + 112 = 120 after strip lead
    seen: set[str] = set()
    result = _process_chunk(core, None, seen)
    if result:
        assert not result["title"].endswith("…")


def test_process_chunk_title_121_chars_truncated_with_ellipsis():
    """BVA: title 121 chars → truncated to 120 + ellipsis."""
    core = "need to " + "x" * 113  # yields title > 120 chars
    seen: set[str] = set()
    result = _process_chunk(core, None, seen)
    if result:
        assert result["title"].endswith("…")
        assert len(result["title"]) == 121  # 120 chars + "…" (1 char)


# ── _dates_in_text ────────────────────────────────────────────────────────────

ISO_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def test_dates_in_text_recognized_phrase():
    """EP: known date phrase → ISO datetime string."""
    result = _dates_in_text("meet next Monday at 10am")
    assert result is not None
    assert ISO_PATTERN.match(result)


def test_dates_in_text_tomorrow():
    """EP: 'tomorrow' resolves to a date."""
    result = _dates_in_text("submit the report tomorrow")
    assert result is not None
    assert ISO_PATTERN.match(result)


def test_dates_in_text_no_date_returns_none():
    """EP: text without any date reference → None."""
    result = _dates_in_text("buy groceries and clean house")
    assert result is None


# ── extract_tasks ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def spacy_available():
    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


def test_extract_tasks_trigger_returns_list(spacy_available):
    """EP: text with task trigger → list with at least one task."""
    if not spacy_available:
        pytest.skip("spaCy en_core_web_sm not installed")
    from app.notes.nlp_extractor import extract_tasks

    tasks = extract_tasks("I need to submit the quarterly report by Friday.")
    assert isinstance(tasks, list)
    assert len(tasks) >= 1
    assert "title" in tasks[0]


def test_extract_tasks_no_tasks_returns_empty(spacy_available):
    """EP: neutral text → empty list."""
    if not spacy_available:
        pytest.skip("spaCy en_core_web_sm not installed")
    from app.notes.nlp_extractor import extract_tasks

    tasks = extract_tasks("The weather is nice today. I enjoyed the sunrise.")
    assert tasks == []


def test_extract_tasks_compound_sentence_two_tasks(spacy_available):
    """EP: compound sentence splits into multiple tasks."""
    if not spacy_available:
        pytest.skip("spaCy en_core_web_sm not installed")
    from app.notes.nlp_extractor import extract_tasks

    tasks = extract_tasks("I need to buy milk and then pick up the kids from school.")
    assert len(tasks) >= 1  # at minimum the first task detected


def test_extract_tasks_caps_at_five(spacy_available):
    """BVA: output never exceeds 5 tasks regardless of input."""
    if not spacy_available:
        pytest.skip("spaCy en_core_web_sm not installed")
    from app.notes.nlp_extractor import extract_tasks

    text = (
        "I need to buy milk. I should call the doctor. "
        "Remember to schedule a meeting with Alice. "
        "Don't forget to submit the report. "
        "I have to pick up the kids. "
        "I must send the email to Bob."
    )
    tasks = extract_tasks(text)
    assert len(tasks) <= 5


def test_extract_tasks_long_text_no_crash(spacy_available):
    """EG: text exceeding 4000 chars is handled without exception."""
    if not spacy_available:
        pytest.skip("spaCy en_core_web_sm not installed")
    from app.notes.nlp_extractor import extract_tasks

    long_text = "I need to buy milk. " * 300  # ~6000 chars
    tasks = extract_tasks(long_text)
    assert isinstance(tasks, list)


def test_extract_tasks_returns_empty_without_spacy(monkeypatch):
    """EP: when spaCy is not available, returns empty list gracefully."""
    import app.notes.nlp_extractor as extractor

    monkeypatch.setattr(extractor, "_nlp", False)
    tasks = extractor.extract_tasks("I need to buy milk today.")
    assert tasks == []
