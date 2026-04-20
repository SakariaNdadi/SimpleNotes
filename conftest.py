import uuid
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"


def make_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"testuser_{uid}",
        "email": f"test_{uid}@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture
def user():
    return make_user()


@pytest.fixture
def registered_user(page: Page, base_url):
    u = make_user()
    page.goto(f"{base_url}/register")
    page.fill("input[name='username']", u["username"])
    page.fill("input[name='email']", u["email"])
    page.fill("input[name='password']", u["password"])
    page.fill("input[name='confirm_password']", u["password"])
    page.click("button[type='submit']")
    expect(page.locator("text=Account created")).to_be_visible()
    return u


def wait_for_alpine(page: Page):
    page.wait_for_selector("aside:not([x-cloak])", timeout=15000)


@pytest.fixture
def logged_in(page: Page, base_url, registered_user):
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", registered_user["username"])
    page.fill("input[name='password']", registered_user["password"])
    page.click("button[type='submit']")
    page.wait_for_url(f"{base_url}/")
    wait_for_alpine(page)
    return registered_user
