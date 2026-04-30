# Project Instructions

## Read First
Read `.claude/PROJECT_STRUCTURE.md` before editing any file. It contains the full module map, dependency graph, and data flows. Do not skip this.

---

## Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (sync), Pydantic Settings
- **Templates**: Jinja2 + HTMX (server-driven partials, not a SPA)
- **LLM**: LiteLLM abstraction — never call provider SDKs directly
- **Job Queue**: `app/jobs/` — RabbitMQ-backed async broker; falls back to `asyncio.create_task()` when `RABBITMQ_URL` is empty or unavailable. Worker process: `app/worker.py`
- **Search**: Meilisearch (full-text) + pgvector (semantic, PostgreSQL only)
- **Auth**: JWT via python-jose, cookies, bcrypt passwords, Fernet encryption
- **DB**: PostgreSQL (dev/prod/integration) | SQLite in-memory (unit tests only)

---

## Docker

Docker is required for all development and integration testing.

```bash
# Full dev stack (app + PostgreSQL + Meilisearch + RabbitMQ + worker)
docker compose -f docker/docker-compose.dev.yml up -d

# Test DB only (pgvector on port 5433)
docker compose -f docker/docker-compose.test.yml up -d
```

---

## Before Editing Any File

- **Routers**: Check which services and dependencies they call. Router changes cascade. Nine routers registered in `main.py`: `auth`, `profile`, `notes`, `labels`, `ai`, `integrations`, `integrations_panel`, `tasks`, `preferences`.
- **models.py**: Any schema change requires checking all services that query that model.
- **auth/utils.py**: Fernet key is lazily initialized on first call to `encrypt_value`/`decrypt_value` via `_get_fernet()` (`@lru_cache`) — stored in the `AppSecret` table, falls back to an ephemeral key when the table is absent (unit test context). Always use `encrypt_value` / `decrypt_value` from this file — never roll your own.
- **config.py**: All env vars flow through the `settings` singleton. Do not read `os.environ` directly in app code. Use `settings.is_postgres` to guard vector operations — do not do manual string checks on `settings.database_url`.
- **Background tasks** (`embed_and_index`): Fire-and-forget via the job broker. Failures are silent. Do not assume indexing succeeded synchronously.
- **HTMX routes**: Return HTML fragments only. Do not return JSON from routes that HTMX calls — except AI endpoints which return both.

---

## Database Rules

- Soft delete only: set `is_deleted=True`. Never hard delete a note except via the permanent delete endpoint (`DELETE /notes/{id}/permanent`).
- Vector column (`embedding`) only exists on PostgreSQL. Guard any vector operation with `settings.is_postgres`.
- Integration tests use savepoint rollback — each test gets a clean slate. Do not commit inside tests.
- Never add a raw `session.commit()` inside a service function that receives an injected `db` session — the router or test controls the transaction boundary.

---

## Testing

### Structure
| Layer | Location | DB |
|-------|----------|----|
| Unit | `tests/unit/` | SQLite in-memory |
| Integration | `tests/integration/` | PostgreSQL `localhost:5433` (docker-compose.test.yml) |
| E2E | `tests/e2e/`, `tests/test_tasks_e2e.py`, `tests/test_notes.py` | Playwright against live server |

### Rules
- Never mock the database in integration tests. Real DB only — savepoint rollback handles isolation.
- Unit tests use SQLite in-memory engine (not TestClient). Acceptable to mock external services (Meili, LLM) at this layer.
- E2E tests use Playwright. Fixtures: `logged_in`, `base_url`, `wait_for_alpine`.
- Always run the relevant test layer after a change before marking done.

### Commands
```bash
# Start test DB first
docker compose -f docker/docker-compose.test.yml up -d

pytest tests/unit/
TEST_DATABASE_URL="postgresql+psycopg://notes:notes@localhost:5433/notes_test" pytest tests/integration/
pytest tests/e2e/ --headed           # requires live server at localhost:8000
pytest tests/test_tasks_e2e.py       # legacy e2e tasks
pytest tests/test_notes.py           # legacy e2e notes
```

### Pre-commit Hook

`.git/hooks/pre-commit` runs automatically on every `git commit` and blocks the commit on any failure:

1. `ruff check` — linting
2. `ruff format --check` — formatting
3. `pytest tests/unit/` — unit tests (SQLite, always runs)
4. `pytest tests/integration/` — integration tests (requires PostgreSQL; start with `docker compose -f docker/docker-compose.test.yml up -d`)
5. `pytest tests/e2e/ tests/test_notes.py tests/test_tasks_e2e.py` — E2E tests (skipped automatically if no server at `localhost:8000`)

To run E2E tests in the hook, start the full dev stack before committing:

```bash
docker compose -f docker/docker-compose.dev.yml up -d
git commit ...
```

To bypass the hook entirely (WIP commits only): `git commit --no-verify`

---

### GitHub Actions

`.github/workflows/ci.yml` — runs on every push/PR to `dev`, `main`:

- `lint`: ruff check + format check
- `unit`: unit tests (SQLite, no services)
- `integration`: integration tests against pgvector/pgvector:pg17 service container

`.github/workflows/e2e.yml` — runs on push/PR to `main` and manual dispatch:

- Starts a PostgreSQL service container, spins up the dev server, runs Playwright E2E tests
- Uploads Playwright report as an artifact on failure

A fresh Fernet key is generated per run — no repository secrets required.

### Known Behavioural Quirks (verified in tests)

**`_save_history` with `max_history=1`**: Net result is 0 history entries. The service adds first, then counts (autoflush: count=1), then prunes `count - max_history + 1 = 1` entries. Test must assert `count == 0`.

**Tasks router filter**: `GET /tasks?filter=local` does NOT exclude discovered tasks. The router always calls `get_discovered_tasks()` in a separate query and renders them regardless of filter. Filter only affects the `get_user_tasks()` (active) list.

**Profile template errors**: The profile template renders `errors.username`, `errors.email`, `errors.new_password` inline, but NOT `errors.current_password`. Integration tests for wrong-password must only assert `status_code == 422`, not check response text.

**`_save_history` max_history guard**: `max_history=0` skips history entirely. `max_history=1` prunes to 0. This is correct algorithmic behavior.

### E2E UI Structure (Playwright)

**Tasks panel**: Clicking "Tasks" in the `aside` sidebar sets `settingsPanel = 'tasks'` which opens a drawer/modal. Panel content loads via HTMX into `#settings-content`. The new-task form is hidden behind `#new-task-toggle` (Alpine `newTaskOpen`). Correct open sequence:

1. `page.locator("aside button", has_text="Tasks").click()`
2. `page.locator("#new-task-toggle").click()`
3. Wait for `form[hx-post='/tasks'] input[name='title']` to be visible.

**HTMX buttons with `opacity-0 group-hover:opacity-100`**: Cannot be clicked via standard Playwright `click()` or `click(force=True)` or `dispatch_event("click")`. Use `htmx.ajax()` via `page.evaluate()` directly:

```python
page.evaluate(f"() => htmx.ajax('DELETE', '/tasks/{uuid}', {{target: '#{task_id}', swap: 'outerHTML'}})")
```

**Alpine `aiEnabled`**: This is a component-local variable on the main `x-data` component, NOT only `$store.app.aiEnabled`. Setting only the store does not make `x-show="aiEnabled && searchQuery"` react. Must set both the store and the component data stack:

```python
page.evaluate("""() => {
    localStorage.setItem('notes-ai', 'true');
    if (window.Alpine) {
        if (Alpine.store('app')) Alpine.store('app').aiEnabled = true;
        document.querySelectorAll('[x-data]').forEach(el => {
            if (el._x_dataStack) {
                el._x_dataStack.forEach(data => { if ('aiEnabled' in data) data.aiEnabled = true; });
            }
        });
    }
}""")
```

**Summary button click**: The note body `<p>` intercepts pointer events over the summary button. Use `dispatch_event("click")` instead of `click()` or `click(force=True)`.

**Sidebar (desktop-hideable)**: The close `×` button is no longer `md:hidden` — the sidebar can be toggled on desktop too. `<main>` uses `:class="sidebarOpen ? 'md:ml-64' : 'md:ml-0'"`. The backdrop overlay remains `md:hidden`. `sidebarOpen` initialises to `window.innerWidth >= 768`.

**Double-click to open composer**: `@dblclick.self` on both `div.flex-1.overflow-y-auto` and `#note-feed` calls `composerOpen ? closeComposer() : openComposer()`. In Playwright use `dispatch_event("dblclick")` on `#note-feed` to avoid child elements intercepting.

**Trash and archive element IDs**: The main feed uses `id="note-{id}"`. The trash feed uses `id="trash-note-{id}"` and the archive feed uses `id="archive-note-{id}"`. Do not use `[id^='note-']` when targeting trash or archive cards — it will never match.

**`.note-actions` hidden buttons**: Action buttons in `note_timeline_item.html` are wrapped in `.note-actions` which has `max-height: 0; overflow: hidden; opacity: 0` by default (CSS, not Tailwind). Like `opacity-0 group-hover:opacity-100` buttons, standard `click()` and `click(force=True)` do not fire HTMX. Use `dispatch_event("click")` for buttons that trigger `hx-get`/`hx-post`/`hx-put`, or use `htmx.ajax()` for `hx-delete`.

**Note card `showSummary`**: Every note card has `x-data="{ showSummary: false, expanded: false }"`. A "Summary" pill button (rendered only when `note.summaries` is non-empty) toggles `showSummary`. The AI summary button (inside `opacity-0 group-hover:opacity-100`) sets `showSummary = true`. The summary container uses `x-show="showSummary"`. To reveal in tests without hover:

```python
page.evaluate("""() => {
    document.querySelectorAll('[x-data]').forEach(el => {
        if (el._x_dataStack) {
            el._x_dataStack.forEach(data => { if ('showSummary' in data) data.showSummary = true; });
        }
    });
}""")
```

---

## Code Rules

- Descriptive identifiers. No single-letter variables.
- No obvious inline comments. Document non-obvious logic only.
- No placeholder code. No TODO stubs unless explicitly requested.
- Apply SOLID principles in OOP contexts.
- Raw code blocks only in responses — no prose wrapping.
- Do not add error handling for scenarios that cannot happen. Trust SQLAlchemy session guarantees and FastAPI dependency injection.

---

## Fixtures Reference

### Integration (`tests/integration/conftest.py`)

| Fixture | Returns |
| --- | --- |
| `engine` | SQLAlchemy engine (session-scoped, PostgreSQL) |
| `db` | Session with savepoint rollback |
| `client` | TestClient with overridden `get_db` |
| `db_user` | `(User, password)` tuple |
| `auth_client` | `(client, user)` with JWT cookie set |
| `db_note` | Note owned by `db_user` |
| `db_task` | NoteTask (status="local", source="manual") owned by `db_user` on `db_note` |
| `db_label` | Label owned by `db_user` |
| `db_llm_config` | UserLLMConfig (openai/gpt-4o-mini, encrypted key) owned by `db_user` |
| `db_discovered_task` | NoteTask (status="discovered", source="nlp") owned by `db_user` on `db_note` |

### Unit (`tests/unit/conftest.py`)

| Fixture | Returns |
| --- | --- |
| `engine` | SQLAlchemy engine (module-scoped, SQLite in-memory) |
| `db` | Session with rollback |
| `unit_user` | `User` |
| `unit_note` | `Note` owned by `unit_user` |
| `unit_task` | `NoteTask` (status="local") on `unit_note` |
