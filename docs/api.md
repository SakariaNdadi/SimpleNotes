# API Reference

Interactive docs available at `/api/docs` when running the server.

## Auth

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/register` | — | Register page |
| POST | `/register` | `username, email, password, confirm_password` | Create account (no verification email sent) |
| GET | `/login` | — | Login page |
| POST | `/login` | `username, password` | Login → sets JWT cookie |
| POST | `/logout` | — | Clear cookie |
| GET | `/verify-email/{token}` | — | Verify email (endpoint exists, not triggered on signup) |
| GET/POST | `/forgot-password` | `email` | Request password reset |
| GET/POST | `/reset-password/{token}` | `password, confirm_password` | Reset password |
| GET/POST | `/profile` | `username, email, current_password, new_password?` | Update profile |

## Notes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notes?offset=N&label_id=X` | Paginated list (HTMX partial) |
| POST | `/notes` | Create note |
| POST | `/notes/search` | Search notes |
| GET | `/notes/trash` | Trashed notes |
| GET | `/notes/archive` | Archived notes |
| GET | `/notes/{id}` | View note |
| GET | `/notes/{id}/edit` | Edit form partial |
| PUT | `/notes/{id}` | Update note |
| POST | `/notes/{id}/archive` | Archive note |
| POST | `/notes/{id}/restore` | Restore from trash/archive |
| DELETE | `/notes/{id}` | Soft delete (trash) |
| DELETE | `/notes/{id}/permanent` | Permanently delete |
| GET | `/notes/{id}/history` | Version history |
| POST | `/notes/{id}/history/{history_id}/restore` | Restore version |

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
| DELETE | `/ai/summary/{note_id}` | Remove summary |
| POST | `/ai/detect-tasks/{note_id}` | Detect tasks/reminders |

## LLM Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/llm` | List configs |
| POST | `/settings/llm` | Add config |
| POST | `/settings/llm/{id}/activate` | Set active |
| DELETE | `/settings/llm/{id}` | Remove config |

## Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List tasks |
| GET | `/tasks/count` | Pending task count (HTMX badge) |
| GET | `/tasks/{id}/edit` | Edit task form |
| PUT | `/tasks/{id}` | Update task |
| POST | `/tasks/{id}/confirm` | Confirm detected task |
| POST | `/tasks/{id}/done` | Mark done |
| POST | `/tasks/{id}/undone` | Mark undone |
| POST | `/tasks/{id}/status` | Toggle status |
| DELETE | `/tasks/{id}/dismiss` | Dismiss task |
| DELETE | `/tasks/{id}` | Delete task |

## Preferences

| Method | Path | Description |
|--------|------|-------------|
| GET | `/preferences` | Preferences page |
| POST | `/preferences/font` | Set font |
| POST | `/preferences/palette` | Set color palette |
| POST | `/preferences/ai-summary-toggle` | Toggle AI summary |
| POST | `/preferences/history-depth` | Set history depth |
| POST | `/preferences/languages` | Set languages |

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
