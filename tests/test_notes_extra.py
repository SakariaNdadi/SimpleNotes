import pytest
from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_composer(page: Page):
    page.get_by_text("New note").click()
    page.locator("textarea[name='description']").wait_for(state="visible")


def _create_note(page: Page, text: str):
    _open_composer(page)
    page.fill("textarea[name='description']", text)
    page.keyboard.press("Control+Enter")
    expect(page.locator("#note-feed")).to_contain_text(text)


def test_edit_note(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note to edit original")
    card = page.locator("#note-feed [id^='note-']").first
    card.hover()
    card.locator("button[hx-get*='/edit']").click()
    edit_area = page.locator("textarea[name='description']")
    edit_area.wait_for(state="visible")
    edit_area.fill("Note after edit")
    page.locator("button[type='submit']").first.click()
    expect(page.locator("#note-feed")).to_contain_text("Note after edit")


def test_permanent_delete(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note for permanent delete")
    card = page.locator("#note-feed [id^='note-']").first
    card.hover()
    card.locator("button[hx-delete]").click()
    page.get_by_text("Trash").click()
    trash_card = page.locator("#note-feed [id^='note-']").first
    expect(trash_card).to_contain_text("Note for permanent delete")
    trash_card.hover()
    trash_card.locator("button[hx-delete*='permanent']").click()
    expect(page.locator("#note-feed")).not_to_contain_text("Note for permanent delete")


def test_filter_notes_by_label(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    page.get_by_text("Add label").click()
    page.locator("input[name='title']").wait_for(state="visible")
    page.locator("input[name='title']").fill("FilterLabel")
    page.locator("form[hx-post='/labels'] button[type='submit']").click()
    expect(page.locator("#label-list")).to_contain_text("FilterLabel")
    _open_composer(page)
    page.fill("textarea[name='description']", "Labeled note content")
    page.keyboard.press("Control+Enter")
    page.locator("#label-list").get_by_text("FilterLabel").click()
    page.locator("#note-feed").wait_for(state="visible")


def test_restore_from_archive(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note for archive restore")
    card = page.locator("#note-feed [id^='note-']").first
    card.hover()
    card.locator("button[hx-post*='archive']").click()
    expect(card).not_to_be_visible()
    page.get_by_text("Archive").click()
    archive_card = page.locator("#note-feed [id^='note-']").first
    expect(archive_card).to_contain_text("Note for archive restore")
    archive_card.hover()
    archive_card.locator("button[hx-post*='restore']").click()
    page.get_by_text("All notes").click()
    expect(page.locator("#note-feed")).to_contain_text("Note for archive restore")
