# Contributing to Notes

Notes is an open-source, self-hosted notes app. Contributions are welcome — from humans and AI agents alike.

## Ways to Contribute

- Fix bugs
- Add features
- Improve docs
- Report issues
- Review pull requests

## Getting Started

1. Fork the repo
2. Follow [docs/setup.md](docs/setup.md) to run locally
3. Create a branch: `git checkout -b feat/your-feature` or `fix/your-bug`
4. Make changes, test them
5. Open a pull request against `master`

## Filing Issues

Use GitHub Issues. Include:

- What you expected vs. what happened
- Steps to reproduce
- Relevant logs or screenshots
- Environment (dev/prod, OS, browser if UI)

Label your issue: `bug`, `enhancement`, `question`, or `docs`.

## Pull Requests

- Keep PRs focused — one concern per PR
- Link the issue your PR addresses (`Closes #123`)
- Describe what changed and why in the PR body
- PRs that break existing behaviour need a migration path or explicit discussion

### Checklist

- [ ] Tested locally (dev setup)
- [ ] No secrets or `.env` files committed
- [ ] Migrations included if models changed — run `uv run alembic revision --autogenerate -m "..."`, commit the generated file in `migrations/versions/`
- [ ] Docs updated if behaviour changed

## Using AI Agents to Contribute

AI-assisted contributions are welcome. If you used an AI agent (Claude Code, Copilot, Cursor, etc.) to write or assist with the code:

- Review the output before submitting — you are responsible for what you open a PR for
- The PR description should still explain the intent and what was changed
- Mention AI assistance in the PR body if the majority of code was AI-generated (e.g. `Generated with Claude Code`)

AI agents can be pointed at this repo and used to fix issues end-to-end. If you do this:

1. Point the agent at a specific open issue
2. Have it follow the setup in [docs/setup.md](docs/setup.md)
3. Run the dev server and verify the change works before submitting
4. Open the PR as normal

## Testing

### Test types

| Type        | Location             | Tool                      | Requires                        |
|-------------|----------------------|---------------------------|---------------------------------|
| Unit        | `tests/unit/`        | pytest + SQLite in-memory | Nothing — runs standalone       |
| Integration | `tests/integration/` | pytest + real PostgreSQL  | PostgreSQL at `localhost:5432`  |
| E2E         | `tests/e2e/`         | Playwright (browser)      | Running dev server at port 8000 |

### Run unit tests

No server or database required:

```bash
uv run pytest tests/unit/ -v
```

### Run integration tests

Integration tests require a PostgreSQL instance with a `notes_test` database. Create it if it doesn't exist:

```bash
psql -U notes -h localhost -c "CREATE DATABASE notes_test;"
```

Run the suite:

```bash
TEST_DATABASE_URL="postgresql+psycopg://notes:notes@localhost:5432/notes_test" uv run pytest tests/integration/ -v
```

The test DB is isolated — each test rolls back its transaction automatically via savepoint. No cleanup needed between runs.

### Run E2E tests

Start the dev server first:

```bash
uv run uvicorn main:app --reload
```

Then run (with a visible browser):

```bash
uv run pytest tests/e2e/ --headed -v
```

Install Playwright browsers if you haven't:

```bash
uv run playwright install chromium
```

### Run everything

```bash
# terminal 1
uv run uvicorn main:app --reload

# terminal 2
uv run pytest tests/unit/ -v
TEST_DATABASE_URL="postgresql+psycopg://notes:notes@localhost:5432/notes_test" uv run pytest tests/integration/ -v
uv run pytest tests/e2e/ --headed -v
```

---

### What tests to write

**Pure logic, no HTTP** → write a unit test in `tests/unit/test_<module>.py`. Use the SQLite in-memory `db` fixture from `tests/unit/conftest.py`. Mock external services (Meili, LLM) at this layer.

**Adding a new endpoint** → write an integration test in the matching `tests/integration/test_<module>.py`.

- Auth endpoints → `tests/integration/test_auth.py`
- Notes endpoints → `tests/integration/test_notes.py`
- Labels → `tests/integration/test_labels.py`
- Tasks → `tests/integration/test_tasks.py`
- Profile → `tests/integration/test_profile.py`
- Preferences → `tests/integration/test_preferences.py`

Minimum per endpoint: one happy-path test and one error case (missing auth, bad input, or not found).

**Adding a UI flow** → write an E2E test in `tests/e2e/test_<feature>.py` using Playwright. Use `logged_in` fixture for authenticated flows. Use `expect()` assertions. See known Playwright quirks in `.claude/CLAUDE.md` before writing E2E tests against HTMX/Alpine UI.

**Changing auth or DB models** → update the integration test fixtures in `tests/integration/conftest.py` and any affected test files.

**No tests needed** for: config changes, template-only styling, migrations that don't change behaviour.

---

## Code Style

Linting is handled by [Ruff](https://docs.astral.sh/ruff/):

```bash
uv run ruff check .
uv run ruff format .
```

Run this before opening a PR.

## Project Structure

```
app/
  auth/          # Auth, profile, JWT
  notes/         # Notes CRUD, history, tasks
  labels/        # Labels
  ai/            # LLM config, summary, search
  integrations/  # Google/Microsoft OAuth + calendar
  preferences/   # User preferences
docker/          # Docker Compose files, nginx config
docs/            # Documentation
migrations/      # Alembic migrations
```

## License

MIT. See [LICENSE](LICENSE).
