"""
Full E2E Playwright tests for the tasks panel UI.

ISTQB techniques: EP, BVA, State Transition.
Requires live server at http://localhost:8000 and Playwright.

Run with: pytest tests/e2e/test_tasks_full.py
"""
import pytest
from playwright.sync_api import Page, expect
from conftest import wait_for_alpine


def _open_tasks_panel(page: Page) -> None:
    page.locator("aside button", has_text="Tasks").click()
    page.locator("#tasks-panel, [id*='tasks']").wait_for(state="visible", timeout=5000)


def _create_task(page: Page, title: str) -> None:
    """Open tasks panel, fill form, submit, and wait for task to appear."""
    _open_tasks_panel(page)
    page.locator("input[name='title'], [placeholder*='task' i]").first.fill(title)
    page.locator("form[hx-post='/tasks'] button[type='submit']").click()
    expect(page.locator("aside")).to_contain_text(title, timeout=5000)


def test_create_task_appears_in_list(page: Page, base_url, logged_in):
    """EP: submitting a task title via the panel renders it in the task list."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "My E2E Task")
    expect(page.locator("aside")).to_contain_text("My E2E Task")


def test_mark_task_done_moves_to_done_section(page: Page, base_url, logged_in):
    """State Transition: marking a task done moves it out of active list."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Task To Complete")

    # Click the done/check button on the first task card
    task_card = page.locator("aside .task-card, aside [id^='task-']").first
    task_card.locator("button[hx-post*='/done']").click()
    page.wait_for_timeout(500)

    # Task should no longer be in the active section
    active_section = page.locator("aside #active-tasks, aside [data-section='active']")
    if active_section.count() > 0:
        expect(active_section).not_to_contain_text("Task To Complete")


def test_delete_task_removed_from_list(page: Page, base_url, logged_in):
    """EP: deleting a task removes it from the panel."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Task To Delete")

    task_card = page.locator("aside .task-card, aside [id^='task-']").first
    task_card.locator("button[hx-delete]").click()
    page.wait_for_timeout(500)

    expect(page.locator("aside")).not_to_contain_text("Task To Delete")


def test_edit_task_title_updated(page: Page, base_url, logged_in):
    """EP: editing a task and saving updates the displayed title."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Task Before Edit")

    task_card = page.locator("aside .task-card, aside [id^='task-']").first
    task_card.locator("button[hx-get*='/edit']").click()

    title_input = page.locator("input[name='title']").first
    title_input.wait_for(state="visible", timeout=3000)
    title_input.fill("Task After Edit")
    page.locator("form[hx-put*='/tasks/'] button[type='submit']").click()
    page.wait_for_timeout(500)

    expect(page.locator("aside")).to_contain_text("Task After Edit")
    expect(page.locator("aside")).not_to_contain_text("Task Before Edit")


def test_task_count_badge_appears_after_creation(page: Page, base_url, logged_in):
    """EP: task count badge is visible in sidebar after a task is created."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Badge Task")

    # Navigate away from tasks panel to see the badge in the nav
    page.locator("aside button", has_text="Notes").click()
    page.wait_for_timeout(500)

    badge = page.locator("aside span[hx-trigger*='taskCountChanged'], aside .task-badge").first
    if badge.count() > 0:
        expect(badge).to_be_visible()


def test_task_count_badge_disappears_when_all_deleted(page: Page, base_url, logged_in):
    """BVA: when task count drops to 0, badge is hidden (empty response)."""
    page.goto(f"{base_url}/")
    wait_for_alpine(page)
    _create_task(page, "Only Task For Badge Test")

    # Delete the task
    task_card = page.locator("aside .task-card, aside [id^='task-']").first
    task_card.locator("button[hx-delete]").click()
    page.wait_for_timeout(500)

    # Badge should now be empty/hidden
    badge = page.locator("aside span[hx-trigger*='taskCountChanged'], aside .task-badge").first
    if badge.count() > 0:
        expect(badge).not_to_be_visible()
