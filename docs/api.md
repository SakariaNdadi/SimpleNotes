# API Reference

Interactive docs available at `/api/docs` when running the server.

## Auth

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/register` | — | Register page |
| POST | `/register` | `username, email, password, confirm_password` | Create account |
| GET | `/login` | — | Login page |
| POST | `/login` | `username, password` | Login → sets JWT cookie |
| POST | `/logout` | — | Clear cookie |
| GET | `/verify-email/{token}` | — | Verify email |
| GET/POST | `/forgot-password` | `email` | Request password reset |
| GET/POST | `/reset-password/{token}` | `password, confirm_password` | Reset password |
| GET/POST | `/profile` | `username, email, current_password, new_password?` | Update profile |

## Notes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notes?offset=N&label_id=X` | Paginated list (HTMX partial) |
| POST | `/notes` | Create note |
| GET | `/notes/{id}/edit` | Edit form partial |
| PUT | `/notes/{id}` | Update note |
| DELETE | `/notes/{id}` | Delete note |

## Labels

| Method | Path | Description |
|--------|------|-------------|
| GET | `/labels` | List labels (HTMX partial) |
| POST | `/labels` | Create label |
| PUT | `/labels/{id}` | Update label |
| DELETE | `/labels/{id}` | Delete label |

## AI

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai/search` | Semantic search (body: `query`) |
| POST | `/ai/summary/{note_id}` | Summarize note |
| POST | `/ai/detect-tasks/{note_id}` | Detect tasks/reminders |

## LLM Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/llm` | List configs |
| POST | `/settings/llm` | Add config |
| POST | `/settings/llm/{id}/activate` | Set active |
| DELETE | `/settings/llm/{id}` | Remove config |

## Integrations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/integrations/panel` | Panel partial |
| GET | `/integrations/google/oauth` | Start Google OAuth |
| GET | `/integrations/google/callback` | OAuth callback |
| GET | `/integrations/microsoft/oauth` | Start Microsoft OAuth |
| GET | `/integrations/microsoft/callback` | OAuth callback |
| POST | `/integrations/{provider}/create-task` | Create task/event |
| DELETE | `/integrations/{provider}/disconnect` | Disconnect provider |
