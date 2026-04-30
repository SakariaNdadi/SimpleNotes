# Setup Guide

## Prerequisites

- Docker and Docker Compose

## Development Setup

```bash
# 1. Clone
git clone https://github.com/SakariaNdadi/notes.git && cd notes

# 2. Copy env
cp .env.example .env

# 3. Set a strong SECRET_KEY in .env (32+ chars, used to sign JWT tokens)

# 4. Start the full dev stack
docker compose -f docker/docker-compose.dev.yml up -d
```

Visit [http://localhost:8000](http://localhost:8000).

The dev stack starts: app server, PostgreSQL + pgvector, Meilisearch, RabbitMQ, and a background worker. The Fernet encryption key is generated automatically on first run — no manual step required.

## Production Setup

### Requirements

- Docker & Docker Compose
- Domain with DNS pointing to your server
- SSL certificate (Let's Encrypt recommended)

### Steps

```bash
# 1. Fill .env with production values (see docs/env.md)
# 2. Generate SECRET_KEY: openssl rand -hex 32
# 3. Configure SMTP if you want password reset emails
# 4. Configure Google/Microsoft OAuth if using integrations

docker compose -f docker/docker-compose.prod.yml up -d
```

pgAdmin is available at `http://your-server:5050`. Set `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` in `.env`.

### Enabling HTTPS

Edit `docker/nginx.conf` to uncomment the redirect and add SSL:

```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ...
}
```

Mount your certificates into the `nginx_certs` volume.

## Migrations

Alembic is configured in `migrations/` and wired to `app.database.Base` and `app.config.get_settings()`.

```bash
# Generate a migration after changing models
uv run alembic revision --autogenerate -m "description"

# Apply all pending migrations
uv run alembic upgrade head

# Check current revision
uv run alembic current

# Downgrade one step
uv run alembic downgrade -1
```

Migration files live in `migrations/versions/`. Commit them alongside model changes.
