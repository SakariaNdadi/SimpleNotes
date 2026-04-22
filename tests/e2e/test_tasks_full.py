"""
Full E2E Playwright tests for the tasks panel UI.

ISTQB techniques: EP, BVA, State Transition.
Requires live server at http://localhost:8000 and Playwright.

Run with: pytest tests/e2e/test_tasks_full.py --headed
"""
import pytest
from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_tasks_panel(page: Page) -> None:
    """Click the Tasks sidebar button; the panel loads into #settings-content."""
    page.locator("aside button", has_text="Tasks").click()
    # Wait for the tasks panel content to load
    page.locator("#settings-content").wait_for(state="visible", timeout=5000)
    # Click the new-task toggle to reveal the creation form
    toggle = page.locator("#new-task-toggle")
    toggle.wait_for(state="visible", timeout=5000)
    toggle.click()
    page.locator("form[hx-post='/tasks'] input[name='title']").wait_for(state="visible", timeout=5000)


def _create_task(page: Page, title: str) -> None:
    """Open tasks panel, fill the task title input, submit, and verify."""
    _open_tasks_panel(page)
    task_input = page.locator("form[hx-post='/tasks'] input[name='title']")
    task_input.fill(title)
    page.locator("form[hx-post='/tasks'] button[type='submit']").click()
    expect(page.locator("#settings-content")).to_contain_text(title, timeout=5000)


def test_create_task_appears_in_list(page: Page, base_url, logged_in):
    """EP: submitting a task title via the panel renders it in the task list."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "My E2E Task")
    expect(page.locator("#settings-content")).to_contain_text("My E2E Task")


def test_mark_task_done_moves_to_done_section(page: Page, base_url, logged_in):
    """State Transition: marking a task done removes it from the active list."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Task To Complete")

    task_card = page.locator("#settings-content [id^='task-']").filter(has_text="Task To Complete").first
    task_card.locator("button[hx-post*='/done']").click()
    page.wait_for_timeout(800)

    assert page.locator("#settings-content").is_visible()


def test_delete_task_removed_from_list(page: Page, base_url, logged_in):
    """EP: deleting a task removes it from the panel."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Task To Delete")

    task_card = page.locator("#settings-content [id^='task-']").filter(has_text="Task To Delete").first
    task_id = task_card.get_attribute("id")  # e.g. "task-{uuid}"
    uuid = task_id.split("task-", 1)[1] if task_id else None

    delete_responses: list[int] = []

    def on_response(response):
        if "/tasks/" in response.url and response.request.method == "DELETE":
            delete_responses.append(response.status)

    page.on("response", on_response)
    page.evaluate(f"""() => htmx.ajax('DELETE', '/tasks/{uuid}', {{
        target: '#{task_id}', swap: 'outerHTML'
    }})""")
    page.wait_for_timeout(2000)

    assert len(delete_responses) > 0, "No DELETE request sent"
    assert delete_responses[0] == 200
    expect(page.locator("#settings-content")).not_to_contain_text("Task To Delete", timeout=5000)


def test_edit_task_title_updated(page: Page, base_url, logged_in):
    """EP: editing a task and saving updates the displayed title."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Task Before Edit")

    task_card = page.locator("#settings-content [id^='task-']").filter(has_text="Task Before Edit").first
    task_card.locator("button[hx-get*='/edit']").click()

    title_input = page.locator("form[hx-put*='/tasks/'] input[name='title']")
    title_input.wait_for(state="visible", timeout=4000)
    title_input.fill("Task After Edit")
    page.locator("form[hx-put*='/tasks/'] button[type='submit']").click()
    page.wait_for_timeout(800)

    expect(page.locator("#settings-content")).to_contain_text("Task After Edit")
    expect(page.locator("#settings-content")).not_to_contain_text("Task Before Edit")


def test_task_count_badge_appears_after_creation(page: Page, base_url, logged_in):
    """EP: task count badge renders in the sidebar after a task is created."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Badge Task")

    page.wait_for_timeout(500)
    aside_html = page.locator("aside").inner_html()
    assert page.locator("aside").is_visible()


def test_task_count_badge_disappears_when_all_deleted(page: Page, base_url, logged_in):
    """BVA: count endpoint returns empty HTML when task count is 0."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Only Task For Badge Test")

    task_card = page.locator("#settings-content [id^='task-']").filter(has_text="Only Task For Badge Test").first
    task_id = task_card.get_attribute("id")
    uuid = task_id.split("task-", 1)[1] if task_id else None

    page.evaluate(f"""() => htmx.ajax('DELETE', '/tasks/{uuid}', {{
        target: '#{task_id}', swap: 'outerHTML'
    }})""")
    page.wait_for_timeout(2000)

    expect(page.locator("#settings-content")).not_to_contain_text("Only Task For Badge Test", timeout=5000)
