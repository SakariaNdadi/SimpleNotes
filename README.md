# SimpleNotes

A self-hosted, open-source notes app with AI search, per-note summaries, automatic task detection, and calendar integrations — built for privacy-first users who want full control over their data.

**Stack:** FastAPI · HTMX · Alpine.js · PostgreSQL + pgvector · LiteLLM · RabbitMQ · Docker

---

## Why SimpleNotes?

Most notes apps either lock your data in the cloud or cost money for AI features. SimpleNotes runs on your own server, stores your notes in your own database, and lets you bring any LLM — including fully local ones via Ollama — for AI features. No subscriptions, no telemetry, no vendor lock-in.

---

## Features

### Notes

- Create, edit, and delete notes from a single-page feed
- Infinite scroll with real-time search
- Notes show an "Edited" badge after modification
- Version history — restore any previous version of a note
- Soft delete with a trash/restore flow; permanent delete available
- Archive notes to keep the feed clean without deleting

### Labels

- Create colour-coded labels with titles and descriptions
- Attach a label to any note
- Filter the note feed by label

### AI (bring your own LLM)

- **Semantic search** — query your notes with natural language; uses pgvector embeddings (PostgreSQL) with keyword fallback when no embedding model is configured
- **Per-note summaries** — generate and cache an AI summary for any note with one click; delete the cache to regenerate
- **Automatic task detection** — the app analyses note content with spaCy NLP and an LLM call to surface tasks buried in your notes as discovered items

Configure any LLM provider in Settings → AI / LLM:

| Provider | Notes |
| -------- | ----- |
| OpenAI (`gpt-4o`, etc.) | Cloud, paid |
| Anthropic (`claude-sonnet-4-6`, etc.) | Cloud, paid |
| Google Gemini | Cloud, free tier available |
| Ollama (`gemma3`, `llama3.2`, `deepseek-r1`, etc.) | **Fully local, free** |
| Any OpenAI-compatible endpoint | llama.cpp, vLLM, LM Studio, Jan, etc. |

API keys are encrypted at rest with Fernet symmetric encryption and never exposed in the UI after saving. See [docs/llm-config.md](docs/llm-config.md) for full setup.

### Tasks

- Create tasks manually from the sidebar panel
- Tasks discovered from note content appear as a separate "discovered" list for review
- Confirm a discovered task to promote it to your active list, or dismiss it
- Mark tasks done, edit titles and descriptions, set due dates
- Tasks sync bidirectionally with Google Tasks and Microsoft To Do (via OAuth)

### Calendar Integrations

- Connect Google Calendar and Google Tasks via OAuth
- Connect Microsoft Calendar and Microsoft To Do via OAuth
- Integrations surface in Settings → Integrations; disconnect any time

### Auth

- Register with email and password
- Email verification (link printed to console in dev; real SMTP in prod)
- Login with remember-me JWT cookie (7-day default, configurable)
- Forgot/reset password flow via email
- Profile page: change username, email, or password
- Changing email re-triggers verification

### Privacy & Self-Hosting

- All data lives in your database — PostgreSQL with pgvector
- No external analytics, no tracking, no phone-home
- Bring your own domain and TLS
- LLM calls go directly from your server to your chosen provider — no intermediary

---

## Quick Start (Dev)

Requires Docker and Docker Compose.

```bash
# 1. Clone
git clone https://github.com/SakariaNdadi/notes.git && cd notes

# 2. Configure environment
cp .env.example .env
# Set a strong SECRET_KEY (32+ chars) in .env

# 3. Start the full dev stack
docker compose -f docker/docker-compose.dev.yml up -d
```

Open [http://localhost:8000](http://localhost:8000), register, and click the verification link printed to your terminal.

The dev stack includes PostgreSQL + pgvector, Meilisearch, RabbitMQ, the app server, and a background worker — all wired together automatically.

## Docker (Production)

```bash
cp .env.example .env   # fill in all values — see docs/env.md
docker compose -f docker/docker-compose.prod.yml up -d
```

Production stack includes PostgreSQL + pgvector, nginx reverse proxy, and pgAdmin. See [docs/setup.md](docs/setup.md) for TLS configuration and full production checklist.

---

## Documentation

| Document | Description |
| -------- | ----------- |
| [docs/setup.md](docs/setup.md) | Full installation and configuration guide |
| [docs/env.md](docs/env.md) | All environment variables with defaults |
| [docs/llm-config.md](docs/llm-config.md) | LLM setup — Ollama, OpenAI, Anthropic, custom endpoints |
| [docs/integrations.md](docs/integrations.md) | Google and Microsoft OAuth setup |
| [docs/api.md](docs/api.md) | API reference |

---

## Dev vs Prod

| Feature | Dev | Prod |
| ------- | --- | ---- |
| Database | PostgreSQL + pgvector (docker-compose.dev.yml) | PostgreSQL + pgvector |
| AI search | Semantic if `EMBEDDING_MODEL` set, else keyword | Semantic (pgvector embeddings) |
| Password reset | Link in console | Real SMTP required |
| Email verification | Link in console | Real SMTP required |
| OAuth integrations | Requires real credentials | Requires real credentials |

---

## Contributing

Contributions are welcome — bugs, features, docs, and tests. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, test commands, and guidelines.

---

## License

MIT. See [LICENSE](LICENSE).
