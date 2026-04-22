from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_composer(page: Page):
    page.get_by_text("New note").click()
    page.locator("textarea[name='description']").wait_for(state="visible")


def _open_tasks_panel(page: Page):
    page.locator("aside button", has_text="Tasks").click()
    page.locator("#tasks-panel, [id*='tasks']").wait_for(state="visible", timeout=5000)


def test_tasks_panel_opens(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    tasks_btn = page.locator("aside").get_by_text("Tasks")
    tasks_btn.click()
    page.wait_for_timeout(500)
    expect(page.locator("aside")).to_be_visible()


def test_tasks_panel_visible_after_note_with_task(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_composer(page)
    page.fill("textarea[name='description']", "Buy milk tomorrow at 9am")
    page.keyboard.press("Control+Enter")
    expect(page.locator("#note-feed")).to_contain_text("Buy milk tomorrow at 9am")
    page.locator("aside").get_by_text("Tasks").click()
    page.wait_for_timeout(1000)
