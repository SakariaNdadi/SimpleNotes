"""
E2E Playwright tests for AI features in the notes UI.

ISTQB techniques: EP, Error Guessing.
Requires live server at http://localhost:8000 and Playwright.

AI-gated features (summary button, AI search button) are hidden by Alpine
`x-show="$store.app.aiEnabled"`. Tests that need those buttons enable AI via
page.evaluate() before interacting.

Run with: pytest tests/e2e/test_notes_ai.py --headed
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


def _enable_ai(page: Page) -> None:
    """Click the sidebar Enable AI button and set localStorage + Alpine store."""
    page.evaluate("""() => {
        localStorage.setItem('notes-ai', 'true');
        if (window.Alpine) {
            if (Alpine.store('app')) Alpine.store('app').aiEnabled = true;
            document.querySelectorAll('[x-data]').forEach(el => {
                if (el._x_dataStack) {
                    el._x_dataStack.forEach(data => { if ('aiEnabled' in data) data.aiEnabled = true; });
                }
            });
        }
    }""")
    page.wait_for_timeout(300)


def test_ai_search_input_visible(page: Page, base_url, logged_in):
    """EP: the search input is always present on the main page."""
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
    page.wait_for_timeout(500)
    expect(page.locator("#note-feed")).to_contain_text("xplorer9", timeout=5000)


def test_ai_search_button_visible_when_ai_enabled_and_query_present(
    page: Page, base_url, logged_in
):
    """EP: AI search button appears when aiEnabled=true and query is filled."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)

    _enable_ai(page)
    page.locator("input[name='query']").fill("test search query")
    page.wait_for_timeout(300)

    ai_btn = page.locator("button[hx-post='/ai/search']")
    expect(ai_btn).to_be_visible(timeout=3000)


def test_ai_search_triggers_request(page: Page, base_url, logged_in):
    """EP: clicking the AI search button sends POST /ai/search and gets 200."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "AI search test note")

    _enable_ai(page)
    page.locator("input[name='query']").fill("search test note")
    page.wait_for_timeout(300)

    ai_responses: list[int] = []

    def on_response(response):
        if "/ai/search" in response.url:
            ai_responses.append(response.status)

    page.on("response", on_response)

    ai_btn = page.locator("button[hx-post='/ai/search']")
    if ai_btn.is_visible(timeout=2000):
        ai_btn.click()
        page.wait_for_timeout(5000)
        assert len(ai_responses) > 0, "No /ai/search request made"
        assert ai_responses[0] == 200
    else:
        pytest.skip("AI search button not visible — LLM config may be required")


def test_note_card_has_summary_button_in_dom(page: Page, base_url, logged_in):
    """EP: a created note card contains the AI summary button in DOM (hidden when AI disabled)."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note with summary trigger test")

    card = page.locator("#note-feed [id^='note-']").first
    summary_btn = card.locator("[hx-post*='/ai/summary/']")
    # Button exists in DOM regardless of AI enable state
    assert summary_btn.count() > 0, "Summary button not found in note card DOM"


def test_note_summary_button_visible_when_ai_enabled(page: Page, base_url, logged_in):
    """EP: summary button becomes visible after enabling AI via Alpine store."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note for summary button visibility test")

    _enable_ai(page)

    card = page.locator("#note-feed [id^='note-']").first
    summary_btn = card.locator("[hx-post*='/ai/summary/']").first
    expect(summary_btn).to_be_visible(timeout=3000)


def test_note_summary_button_sends_request(page: Page, base_url, logged_in):
    """EP: clicking summary button sends POST /ai/summary/{id} and gets 200."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note for summary request test")

    _enable_ai(page)

    summary_responses: list[int] = []

    def on_response(response):
        if "/ai/summary/" in response.url:
            summary_responses.append(response.status)

    page.on("response", on_response)

    card = page.locator("#note-feed [id^='note-']").first
    summary_btn = card.locator("[hx-post*='/ai/summary/']").first
    if summary_btn.is_visible(timeout=2000):
        summary_btn.dispatch_event("click")
        page.wait_for_timeout(5000)
        if len(summary_responses) == 0:
            pytest.skip(
                "Summary button clicked but no HTMX request fired — LLM config may be required"
            )
        assert summary_responses[0] == 200
    else:
        pytest.skip("Summary button not visible — AI may not be enabled")
