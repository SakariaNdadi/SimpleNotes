from playwright.sync_api import Page, expect


def test_register_success(page: Page, base_url, user):
    page.goto(f"{base_url}/register")
    page.fill("input[name='username']", user["username"])
    page.fill("input[name='email']", user["email"])
    page.fill("input[name='password']", user["password"])
    page.fill("input[name='confirm_password']", user["password"])
    page.click("button[type='submit']")
    expect(page.locator("text=Account created")).to_be_visible()


def test_register_duplicate_username(page: Page, base_url, registered_user):
    page.goto(f"{base_url}/register")
    page.fill("input[name='username']", registered_user["username"])
    page.fill("input[name='email']", "different@example.com")
    page.fill("input[name='password']", registered_user["password"])
    page.fill("input[name='confirm_password']", registered_user["password"])
    page.click("button[type='submit']")
    expect(page.locator("text=Username already taken")).to_be_visible()


def test_register_password_mismatch(page: Page, base_url, user):
    page.goto(f"{base_url}/register")
    page.fill("input[name='username']", user["username"])
    page.fill("input[name='email']", user["email"])
    page.fill("input[name='password']", user["password"])
    page.fill("input[name='confirm_password']", "WrongPass999!")
    page.click("button[type='submit']")
    expect(page.locator("text=Passwords do not match")).to_be_visible()


def test_login_success(page: Page, base_url, registered_user):
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", registered_user["username"])
    page.fill("input[name='password']", registered_user["password"])
    page.click("button[type='submit']")
    page.wait_for_url(f"{base_url}/")


def test_login_invalid_credentials(page: Page, base_url):
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", "nobody")
    page.fill("input[name='password']", "wrongpassword")
    page.click("button[type='submit']")
    expect(page.locator("text=Invalid username or password")).to_be_visible()


def test_logout(page: Page, base_url, logged_in):
    page.get_by_text("Sign out").click()
    page.wait_for_url(f"{base_url}/login")
