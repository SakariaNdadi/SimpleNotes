# Notes

Self-hosted, open-source notes app with AI search/summary, calendar integrations, and full auth.

**Stack:** FastAPI · HTMX · Alpine.js · SQLite (dev) · PostgreSQL + pgvector (prod) · LiteLLM · Docker

---

## Quick Start (Dev)

```bash
cp .env.example .env          # configure as needed
uv sync
uv run uvicorn main:app --reload
```

Open http://localhost:8000 — register, verify (link printed to console in dev), log in.

## Docker (Dev)

```bash
cd docker
docker compose up
```

## Docker (Production)

```bash
cp .env.example .env          # fill in all values
cd docker
docker compose -f docker-compose.prod.yml up -d
```

See [docs/setup.md](docs/setup.md) for full production setup.

---

## Features

- **Auth** — register, email verification, login, forgot/reset password, profile management
- **Notes** — create, edit (shows "Edited" badge), delete, infinite scroll feed
- **Labels** — organise notes with titled/described labels, filter feed by label
- **AI** — semantic search, per-note summaries, automatic task detection from note content
- **Self-hosted LLMs** — connect Ollama (Gemma, DeepSeek, Llama), any OpenAI-compatible endpoint, or cloud APIs
- **Calendar integrations** — Google Calendar/Tasks and Microsoft Calendar/To Do via OAuth
- **Single-page UI** — Gemini-style interface, sidebar navigation, no page reloads

---

## Docs

| Document | Description |
|----------|-------------|
| [docs/setup.md](docs/setup.md) | Full installation & configuration guide |
| [docs/env.md](docs/env.md) | All environment variables |
| [docs/llm-config.md](docs/llm-config.md) | LLM setup (Ollama, OpenAI, Anthropic, etc.) |
| [docs/integrations.md](docs/integrations.md) | Google & Microsoft OAuth setup |
| [docs/api.md](docs/api.md) | API reference |
