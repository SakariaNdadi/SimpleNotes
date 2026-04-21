# Project Instructions

## Read First
Read `.claude/PROJECT_STRUCTURE.md` before editing any file. It contains the full module map, dependency graph, and data flows. Do not skip this.

---

## Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (sync), Pydantic Settings
- **Templates**: Jinja2 + HTMX (server-driven partials, not a SPA)
- **LLM**: LiteLLM abstraction — never call provider SDKs directly
- **Search**: Meilisearch (full-text) + pgvector (semantic, PostgreSQL only)
- **Auth**: JWT via python-jose, cookies, bcrypt passwords, Fernet encryption
- **DB**: SQLite (dev/unit tests) or PostgreSQL (integration/prod)

---

## Before Editing Any File

- **Routers**: Check which services and dependencies they call. Router changes cascade.
- **models.py**: Any schema change requires checking all services that query that model.
- **auth/utils.py**: Fernet key is generated at startup in `main.py`. Encryption/decryption must use `fernet_encrypt` / `fernet_decrypt` from this file — never roll your own.
- **config.py**: All env vars flow through the `settings` singleton. Do not read `os.environ` directly in app code.
- **Background tasks** (`embed_and_index`): Fire-and-forget. Failures are silent. Do not assume indexing succeeded synchronously.
- **HTMX routes**: Return HTML fragments only. Do not return JSON from routes that HTMX calls — except AI endpoints which return both.

---

## Database Rules

- Soft delete only: set `is_deleted=True`. Never hard delete a note except via the permanent delete endpoint (`DELETE /notes/{id}/permanent`).
- Vector column (`embedding`) only exists on PostgreSQL. Guard any vector operation with a config check (`settings.database_url` contains `postgresql`).
- Integration tests use savepoint rollback — each test gets a clean slate. Do not commit inside tests.
- Never add a raw `session.commit()` inside a service function that receives an injected `db` session — the router or test controls the transaction boundary.

---

## Testing

### Structure
| Layer | Location | DB |
|-------|----------|----|
| Unit | `tests/` | SQLite in-memory |
| Integration | `tests/integration/` | PostgreSQL `localhost:5433` (real DB, no mocks) |
| E2E | `tests/test_tasks_e2e.py`, `tests/test_notes.py` | Playwright against live server |

### Rules
- Never mock the database in integration tests. Real DB only — savepoint rollback handles isolation.
- Unit tests use `TestClient` with SQLite. Acceptable to mock external services (Meili, LLM) at this layer.
- E2E tests use Playwright. Fixtures: `logged_in`, `base_url`, `wait_for_alpine`.
- Always run the relevant test layer after a change before marking done.

### Commands
```bash
pytest tests/                        # unit
pytest tests/integration/            # integration (requires postgres)
pytest tests/test_tasks_e2e.py       # e2e (requires live server + playwright)
pytest tests/test_notes.py           # e2e notes
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

## Fixtures Reference (`tests/integration/conftest.py`)

| Fixture | Returns |
|---------|---------|
| `engine` | SQLAlchemy engine (session-scoped) |
| `db` | Session with savepoint rollback |
| `client` | TestClient with overridden `get_db` |
| `db_user` | `(User, password)` tuple |
| `auth_client` | `(client, user)` with JWT cookie set |
| `db_note` | Note owned by `db_user` |
| `db_task` | NoteTask owned by `db_user` on `db_note` |
