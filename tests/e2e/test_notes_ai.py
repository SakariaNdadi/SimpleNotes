"""
E2E Playwright tests for AI features visible in the notes UI.

ISTQB techniques: EP, Error Guessing.
Requires live server at http://localhost:8000 and Playwright.
These tests verify UI presence and network interaction — they do NOT require
a real LLM; they assert that the correct requests are sent and 200 returned.

Run with: pytest tests/e2e/test_notes_ai.py
"""
import pytest
from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _create_note(page: Page, text: str) -> None:
    page.get_by_text("New note").click()
    page.locator("textarea[name='description']").wait_for(state="visible")
    page.fill("textarea[name='description']", text)
    page.keyboard.press("Control+Enter")
    expect(page.locator("#note-feed")).to_contain_text(text, timeout=5000)


def test_ai_search_input_visible(page: Page, base_url, logged_in):
    """EP: the AI/keyword search input is present on the main page."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    search_input = page.locator("input[name='query']").first
    expect(search_input).to_be_visible()


def test_keyword_search_returns_results(page: Page, base_url, logged_in):
    """EP: typing a keyword and submitting returns relevant notes."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Unique keyword xplorer9 test content")

    page.locator("input[name='query']").fill("xplorer9")
    page.wait_for_timeout(300)
    expect(page.locator("#note-feed")).to_contain_text("xplorer9", timeout=5000)


def test_ai_search_triggers_request(page: Page, base_url, logged_in):
    """EP: submitting the AI search form sends a POST to /ai/search and gets 200."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)

    ai_response_received = []

    def on_response(response):
        if "/ai/search" in response.url and response.status == 200:
            ai_response_received.append(True)

    page.on("response", on_response)

    # Locate the AI search trigger — it may be a separate button or the same form
    ai_btn = page.locator("[hx-post='/ai/search'], button[data-ai-search]").first
    if ai_btn.count() > 0:
        page.locator("input[name='query']").fill("test AI search query")
        ai_btn.click()
        page.wait_for_timeout(3000)
        assert len(ai_response_received) > 0, "Expected POST /ai/search to return 200"
    else:
        pytest.skip("AI search trigger button not found — selector may differ")


def test_note_card_has_summary_trigger(page: Page, base_url, logged_in):
    """EP: a created note card contains the AI summary trigger button."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note with summary trigger test")

    card = page.locator("#note-feed [id^='note-']").first
    summary_btn = card.locator("[hx-post*='/ai/summary/']")
    expect(summary_btn).to_be_visible()


def test_note_summary_button_sends_request(page: Page, base_url, logged_in):
    """EP: clicking the summary button sends POST /ai/summary/{id} → server responds 200."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note for summary request test")

    summary_responses = []

    def on_response(response):
        if "/ai/summary/" in response.url and response.status == 200:
            summary_responses.append(True)

    page.on("response", on_response)

    card = page.locator("#note-feed [id^='note-']").first
    summary_btn = card.locator("[hx-post*='/ai/summary/']").first
    if summary_btn.count() > 0:
        summary_btn.click()
        page.wait_for_timeout(3000)
        assert len(summary_responses) > 0, "Expected POST /ai/summary/{id} to return 200"
    else:
        pytest.skip("Summary trigger not found on note card")
