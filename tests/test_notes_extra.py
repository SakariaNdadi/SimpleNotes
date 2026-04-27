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
    note_id = card.get_attribute("id").removeprefix("note-")
    # edit button is hidden in .note-actions (max-height:0); dispatch_event bypasses visibility
    card.locator("button[hx-get*='/edit']").dispatch_event("click")
    edit_area = page.locator(f"#note-{note_id} textarea[name='description']")
    edit_area.wait_for(state="visible")
    edit_area.fill("Note after edit")
    page.locator(f"#note-{note_id} button[type='submit']").click()
    expect(page.locator("#note-feed")).to_contain_text("Note after edit")


def test_permanent_delete(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_note(page, "Note for permanent delete")
    card = page.locator("#note-feed [id^='note-']").first
    note_id = card.get_attribute("id").removeprefix("note-")
    page.evaluate(
        f"() => htmx.ajax('DELETE', '/notes/{note_id}', {{target: '#note-{note_id}', swap: 'outerHTML'}})"
    )
    expect(page.locator(f"#note-{note_id}")).not_to_be_visible()
    page.locator("aside button", has_text="Trash").click()
    page.locator(f"#trash-note-{note_id}").wait_for(state="visible")
    trash_card = page.locator(f"#trash-note-{note_id}")
    expect(trash_card).to_contain_text("Note for permanent delete")
    page.once("dialog", lambda d: d.accept())
    trash_card.locator("button[hx-delete*='permanent']").click()
    expect(page.locator(f"#trash-note-{note_id}")).not_to_be_visible()


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
    note_id = card.get_attribute("id").removeprefix("note-")
    card.locator("button[hx-post*='archive']").dispatch_event("click")
    expect(page.locator(f"#note-{note_id}")).not_to_be_visible()
    page.locator("aside button", has_text="Archive").click()
    page.locator(f"#archive-note-{note_id}").wait_for(state="visible")
    archive_card = page.locator(f"#archive-note-{note_id}")
    expect(archive_card).to_contain_text("Note for archive restore")
    archive_card.locator("button[hx-post*='restore']").click()
    page.locator("aside button", has_text="All notes").click()
    expect(page.locator("#note-feed")).to_contain_text("Note for archive restore")
