# Elbilspriser — Backend

## Prerequisites

- Python 3.12
- [uv](https://github.com/astral-sh/uv)
- PostgreSQL 15 with TimescaleDB and PostGIS extensions
- Playwright system dependencies (Chromium)

## Local dev setup

```bash
# Install dependencies
uv sync

# Install Playwright browser
uv run playwright install chromium

# Copy and fill in secrets
cp .env.example .env

# Activate the virtualenv (optional — uv run handles it automatically)
source .venv/bin/activate
```

## Run migrations

```bash
uv run alembic upgrade head
```

## Run the API server

```bash
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## Run a crawler manually

```bash
# Clever (Playwright)
uv run python -m crawlers.clever

# OCPI crawlers
uv run python -m crawlers.spirii
uv run python -m crawlers.monta
```

## Install and enable systemd units (production)

```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# API
sudo systemctl enable --now elbilspriser-api.service

# Clever crawler
sudo systemctl enable --now crawler-clever.timer

# OCPI crawlers
sudo systemctl enable --now crawler-ocpi-hourly.timer
```
