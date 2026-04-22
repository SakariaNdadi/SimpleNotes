from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_composer(page: Page):
    page.get_by_text("New note").click()
    page.locator("textarea[name='description']").wait_for(state="visible")


def test_create_note(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "My test note content")
    page.keyboard.press("Control+Enter")
    expect(page.locator("#note-feed")).to_contain_text("My test note content")


def test_create_note_via_button(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "Note via button")
    page.locator("form[hx-post='/notes'] button[type='submit']").click()
    expect(page.locator("#note-feed")).to_contain_text("Note via button")


def test_delete_note(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "Note to delete")
    page.keyboard.press("Control+Enter")
    card = page.locator("#note-feed [id^='note-']").first
    expect(card).to_contain_text("Note to delete")
    card.hover()
    card.locator("button[hx-delete]").click()
    expect(card).not_to_be_visible()


def test_archive_note(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "Note to archive")
    page.keyboard.press("Control+Enter")
    card = page.locator("#note-feed [id^='note-']").first
    card.hover()
    card.locator("button[hx-post*='archive']").click()
    expect(card).not_to_be_visible()
    page.get_by_text("Archive").click()
    expect(page.locator("#note-feed")).to_contain_text("Note to archive")


def test_restore_from_trash(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "Note for trash restore")
    page.keyboard.press("Control+Enter")
    card = page.locator("#note-feed [id^='note-']").first
    card.hover()
    card.locator("button[hx-delete]").click()
    page.get_by_text("Trash").click()
    trash_card = page.locator("#note-feed [id^='note-']").first
    expect(trash_card).to_contain_text("Note for trash restore")
    trash_card.hover()
    trash_card.locator("button[hx-post*='restore']").click()
    page.get_by_text("All notes").click()
    expect(page.locator("#note-feed")).to_contain_text("Note for trash restore")


def test_search_notes(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "Unique searchable content xyz123")
    page.keyboard.press("Control+Enter")
    page.locator("input[name='query']").fill("xyz123")
    expect(page.locator("#note-feed")).to_contain_text(
        "Unique searchable content xyz123"
    )
