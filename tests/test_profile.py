import uuid
from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_profile_panel(page: Page):
    page.locator("button", has_text=page.locator("aside").inner_text()).first.click()


def _go_to_profile(page: Page, base_url, logged_in):
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    page.locator("aside button").filter(has_text=logged_in["username"]).click()
    page.locator("#settings-content input[name='username']").wait_for(state="visible")


def test_update_username(page: Page, base_url, logged_in):
    _go_to_profile(page, base_url, logged_in)
    new_username = f"updated_{uuid.uuid4().hex[:6]}"
    page.locator("#settings-content input[name='username']").fill(new_username)
    page.locator("#settings-content input[name='current_password']").fill(
        logged_in["password"]
    )
    page.locator("#settings-content button[type='submit']").click()
    expect(page.locator("text=Profile updated")).to_be_visible()


def test_wrong_current_password(page: Page, base_url, logged_in):
    # profile template does not render errors.current_password; verify update does NOT succeed
    _go_to_profile(page, base_url, logged_in)
    page.locator("#settings-content input[name='current_password']").fill(
        "WrongPassword999!"
    )
    page.locator("#settings-content button[type='submit']").click()
    expect(page.locator("text=Profile updated")).not_to_be_visible()
    expect(
        page.locator("#settings-content input[name='current_password']")
    ).to_be_visible()
