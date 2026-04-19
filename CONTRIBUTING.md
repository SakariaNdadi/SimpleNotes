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
