# Project Structure & File Connections

Read this before editing any file. It shows what connects to what.

---

## Entry Point

**`main.py`** — App init, mounts static files, registers all routers, startup hooks (Fernet key, DB tables, Meili index).

Routers registered: auth, notes, labels, ai, integrations, tasks, preferences, profile

---

## Module Map

### Auth — `app/auth/`
| File | Role |
|------|------|
| `router.py` | Login/register/reset endpoints; `get_current_user()` + `require_user()` dependencies used by ALL other routers |
| `service.py` | User CRUD, `authenticate_user()`, email verification (FastAPI-Mail) |
| `utils.py` | `hash_password()`, JWT create/decode, Fernet encrypt/decrypt |
| `profile_router.py` | Profile view/update endpoints |

**Before editing auth:** Any router using `require_user` depends on `router.py:get_current_user`. JWT secret and cookie name are in `app/config.py`.

---

### Notes — `app/notes/`
| File | Role |
|------|------|
| `router.py` | CRUD endpoints; on create triggers `embed_and_index()` + `_nlp_discover()` |
| `service.py` | DB CRUD, `_save_history()` (auto-prunes via preferences), soft delete |
| `nlp_extractor.py` | Regex + spaCy task extraction from note text |
| `task_service.py` | NoteTask CRUD; `save_tasks()`, `confirm_task()`, `dismiss_task()` |
| `tasks_router.py` | `/tasks` endpoints |
| `summary_service.py` | NoteSummary get/save/delete |

**Before editing notes router:** Changes to note creation affect `embed_and_index()` (search), NLP extraction, and history. Check `app/search/hybrid.py`.

**Before editing task_service:** Tasks have `source` (llm/nlp/manual) and `status` (local/discovered). Confirm vs dismiss changes status, not source.

---

### AI — `app/ai/`
| File | Role |
|------|------|
| `router.py` | Summary, semantic search, task detection endpoints; LLM config management |
| `service.py` | LiteLLM wrapper; `_get_active_config()`, `complete()`, fallback httpx for OpenAI-compat |

**Before editing AI service:** Active LLM config is per-user (`UserLLMConfig` model). API keys are Fernet-encrypted (see `app/auth/utils.py`). LiteLLM handles multi-provider routing.

---

### Search — `app/search/`
| File | Role |
|------|------|
| `hybrid.py` | `hybrid_search()` merges Meili + pgvector; `embed_and_index()` background task called from notes router |
| `meili.py` | Meilisearch: `setup_index()`, `index_note()`, `search()`, `delete_note()` |
| `embeddings.py` | `get_embedding()` via LiteLLM |
| `vector.py` | pgvector: `store_embedding()`, `similarity_search()` (cosine, HNSW index) |

**Before editing search:** Vector search only works with PostgreSQL + `EMBEDDING_MODEL` env var. SQLite uses Meili-only fallback. `embed_and_index()` is a background task — failures are silent.

---

### Labels — `app/labels/`
| File | Role |
|------|------|
| `router.py` | Label CRUD endpoints |
| `service.py` | DB ops; uniqueness constraint on `(user_id, title)` |

**Before editing labels:** Notes have optional `label_id` FK. Deleting a label sets notes' label to NULL (check cascade in `app/models.py`).

---

### Integrations — `app/integrations/`
| File | Role |
|------|------|
| `router.py` | OAuth flow + `/create-task` endpoints |
| `google.py` | Google OAuth exchange, token dict |
| `microsoft.py` | Microsoft/Azure OAuth via msal |
| `panel_router.py` | UI for managing connected accounts |

**Before editing integrations:** OAuth tokens stored encrypted in `CalendarToken` model. Fernet key from startup hook in `main.py`.

---

### Preferences — `app/preferences/`
| File | Role |
|------|------|
| `router.py` | GET/PUT preferences |
| `service.py` | `get_or_create_prefs()` (lazy init), `update_prefs()` (whitelist), `get_languages()` |

**Before editing preferences:** `max_edit_history` affects `_save_history()` in `app/notes/service.py`. `save_ai_summaries` affects AI summary router.

---

## Models (`app/models.py`) — Relationship Map

```
User
 ├── Note (one-to-many)
 │    ├── NoteTask (one-to-many)
 │    ├── NoteSummary (one-to-one)
 │    └── NoteHistory (one-to-many)
 ├── Label (one-to-many)
 ├── UserLLMConfig (one-to-many, one active)
 ├── CalendarToken (one-to-many, per provider)
 ├── UserPreferences (one-to-one)
 ├── PasswordResetToken
 └── EmailVerificationToken
```

---

## Key Data Flows

### Note Created
```
POST /notes
  → service.create_note() → DB
  → embed_and_index() [background] → Meili + pgvector
  → _nlp_discover() → extract_tasks() → save_tasks(source="nlp", status="discovered")
```

### Search
```
POST /ai/search
  → hybrid_search() → Meili (keyword) + pgvector (semantic) → merged results
  → ai_service.complete() → re-rank + generate answer
```

### AI Task Detection
```
POST /ai/detect-tasks/{note_id}
  → ai_service.complete() with note text
  → save_tasks(source="llm", status="local")
```

### Auth Flow
```
POST /login → authenticate_user() → JWT cookie (7 days)
Every protected route → get_current_user() → decodes JWT → fetches User from DB
```

---

## Config (`app/config.py`)

Key env vars:
- `DATABASE_URL` — SQLite or PostgreSQL
- `SECRET_KEY` — JWT signing
- `EMBEDDING_MODEL` — enables vector search (optional)
- `MEILISEARCH_URL` / `MEILISEARCH_API_KEY`
- `MAIL_*` — email settings for verification/reset

---

## Templates (`app/templates/`)

HTMX-driven partials. Routes return HTML fragments, not JSON (except AI endpoints which return both).

Key partials: `note_list.html`, `note_timeline_item.html`, `note_edit_form.html`, `task_prompt.html`, `ai_summary.html`

---

## Cross-cutting Concerns

| Concern | Where |
|---------|-------|
| Encryption (tokens, API keys) | `app/auth/utils.py` — `fernet_encrypt/decrypt` |
| Current user injection | `app/auth/router.py` — `require_user` dependency |
| DB session | `app/database.py` — `get_db()` dependency |
| LLM abstraction | `app/ai/service.py` — wraps LiteLLM |
| Settings/config | `app/config.py` — `settings` singleton |
