# Environment Variables

| Variable | Default | Required | Description |
| -------- | ------- | -------- | ----------- |
| `ENV` | `dev` | No | `dev` or `prod` |
| `SECRET_KEY` | *(weak default)* | **Yes** | JWT signing key (32+ chars) |
| `DATABASE_URL` | *(set by Docker Compose)* | **Yes** | SQLAlchemy connection string |
| `RABBITMQ_URL` | *(empty)* | No | RabbitMQ connection string (e.g. `amqp://guest:guest@localhost:5672/`). Empty = asyncio fallback |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | No | JWT expiry |
| `APP_BASE_URL` | `http://localhost:8000` | **Yes (prod)** | Used in OAuth redirects and email links |
| `MAIL_USERNAME` | *(empty)* | No | SMTP username |
| `MAIL_PASSWORD` | *(empty)* | No | SMTP password |
| `MAIL_FROM` | *(empty)* | No | From address for emails |
| `MAIL_SERVER` | `smtp.gmail.com` | No | SMTP host |
| `MAIL_PORT` | `587` | No | SMTP port |
| `MAIL_STARTTLS` | `true` | No | |
| `MAIL_SSL_TLS` | `false` | No | |
| `GOOGLE_CLIENT_ID` | *(empty)* | No | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | *(empty)* | No | Google OAuth Client Secret |
| `MICROSOFT_CLIENT_ID` | *(empty)* | No | Microsoft OAuth App ID |
| `MICROSOFT_CLIENT_SECRET` | *(empty)* | No | Microsoft OAuth Client Secret |
| `MICROSOFT_TENANT_ID` | `common` | No | `common` or your tenant ID |
| `MEILI_URL` | *(empty)* | No | Meilisearch URL (e.g. `http://localhost:7700`) |
| `MEILI_KEY` | *(empty)* | No | Meilisearch master key |
| `EMBEDDING_MODEL` | *(empty)* | No | LiteLLM embedding model (e.g. `text-embedding-3-small`, `ollama/nomic-embed-text`). Empty = keyword search only |
| `EMBEDDING_DIMENSIONS` | `1536` | No | Dimension count — must match the model (OpenAI: 1536, nomic-embed-text: 768, all-minilm: 384) |
| `POSTGRES_DB` | `notes` | Prod | PostgreSQL database name |
| `POSTGRES_USER` | `notes` | Prod | PostgreSQL user |
| `POSTGRES_PASSWORD` | `changeme` | Prod | PostgreSQL password |
| `PGADMIN_EMAIL` | `admin@admin.com` | Prod | pgAdmin login email |
| `PGADMIN_PASSWORD` | `changeme` | Prod | pgAdmin login password |

## Notes

- **Fernet encryption key**: automatically generated and stored in the database on first run. No env var required.
- **`RABBITMQ_URL`**: provided automatically by `docker-compose.dev.yml`. Set manually only for custom deployments. When empty, background jobs run in-process via `asyncio`.
- **`DATABASE_URL`**: set automatically by Docker Compose via the `db` service. Override only when connecting to an external database.

## Dev vs Prod differences

| Feature | Dev | Prod |
| ------- | --- | ---- |
| Database | PostgreSQL + pgvector (docker-compose.dev.yml) | PostgreSQL + pgvector |
| Password reset email | Printed to console | Real SMTP required |
| AI search | Semantic if `EMBEDDING_MODEL` set, else keyword | Semantic (pgvector) |
| OAuth | Requires real credentials | Requires real credentials |
| pgAdmin | Port 5050 | Port 5050 |
