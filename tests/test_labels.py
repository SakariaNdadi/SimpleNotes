from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_add_label(page: Page):
    page.get_by_text("Add label").click()
    page.locator("input[name='title']").wait_for(state="visible")


def test_create_label(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_add_label(page)
    page.locator("input[name='title']").fill("My Label")
    page.locator("form[hx-post='/labels'] button[type='submit']").click()
    expect(page.locator("#label-list")).to_contain_text("My Label")


def test_delete_label(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _open_add_label(page)
    page.locator("input[name='title']").fill("Label to delete")
    page.locator("form[hx-post='/labels'] button[type='submit']").click()
    expect(page.locator("#label-list")).to_contain_text("Label to delete")
    label_item = page.locator("#label-list [id^='label-']").filter(
        has_text="Label to delete"
    )
    label_id = label_item.get_attribute("id").removeprefix("label-")
    page.evaluate(
        f"() => htmx.ajax('DELETE', '/labels/{label_id}', {{target: '#label-{label_id}', swap: 'outerHTML'}})"
    )
    expect(page.locator("#label-list")).not_to_contain_text("Label to delete")
