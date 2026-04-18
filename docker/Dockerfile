FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (layer-cached separately from source)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev && uv run python -m spacy download en_core_web_sm

# Copy source
COPY . .

# Non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
