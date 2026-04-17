# Setup Guide

## Prerequisites

- Python 3.13+ (or Docker)
- [uv](https://github.com/astral-sh/uv) (Python package manager)

## Development Setup

```bash
# 1. Clone
git clone https://github.com/your-repo/notes.git && cd notes

# 2. Copy env
cp .env.example .env

# 3. Generate a Fernet key for encrypting API keys/tokens
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste output into FERNET_KEY in .env

# 4. Set a strong SECRET_KEY in .env

# 5. Install deps
uv sync

# 6. Run
uv run uvicorn main:app --reload
```

Visit http://localhost:8000

**Email verification in dev:** Links are printed to the server console — no SMTP needed.

## Production Setup

### Requirements
- Docker & Docker Compose
- Domain with DNS pointing to your server
- SSL certificate (Let's Encrypt recommended)

### Steps

```bash
# 1. Fill .env with production values (see docs/env.md)
# 2. Generate SECRET_KEY: openssl rand -hex 32
# 3. Generate FERNET_KEY (see above)
# 4. Configure SMTP for real email sending
# 5. Configure Google/Microsoft OAuth if using integrations

cd docker
docker compose -f docker-compose.prod.yml up -d
```

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

Using Alembic (auto-generated from SQLAlchemy models):

```bash
# Init (first time)
uv run alembic init migrations
# Edit migrations/env.py to import app.database.Base and use DATABASE_URL from config

# Generate migration
uv run alembic revision --autogenerate -m "description"

# Apply
uv run alembic upgrade head
```
