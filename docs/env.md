# Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ENV` | `dev` | No | `dev` or `prod` |
| `SECRET_KEY` | *(weak default)* | **Yes** | JWT signing key (32+ chars) |
| `FERNET_KEY` | *(auto-generated)* | **Yes (prod)** | Encryption key for tokens/API keys |
| `DATABASE_URL` | `sqlite:///./notes.db` | No | SQLAlchemy connection string |
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
| `POSTGRES_PASSWORD` | `changeme` | Prod | PostgreSQL password |
| `PGADMIN_EMAIL` | `admin@admin.com` | Prod | pgAdmin login email |
| `PGADMIN_PASSWORD` | `changeme` | Prod | pgAdmin login password |

## Dev vs Prod differences

| Feature | Dev | Prod |
|---------|-----|------|
| Database | SQLite | PostgreSQL + pgvector |
| Email on signup | Disabled | Disabled |
| Password reset email | Printed to console | Real SMTP required |
| AI search | Keyword fallback | pgvector semantic search |
| OAuth | Requires real credentials | Requires real credentials |
| pgAdmin | Port 5050 | Port 5050 |
