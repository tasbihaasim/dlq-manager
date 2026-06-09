# dlq-manager

A webhook Dead Letter Queue (DLQ) management system built with FastAPI, Celery, RabbitMQ, Redis, and PostgreSQL. Ingests webhook events, retries failed processing automatically, and surfaces failures in a real-time dashboard.

## Features

- **Webhook ingestion** with HMAC-SHA256 signature verification
- **Async processing** via Celery workers backed by RabbitMQ
- **Automatic retries** with exponential backoff (up to 3 attempts)
- **Dead Letter Queue** — failed events are captured and stored after retries are exhausted
- **Real-time dashboard** — live event feed and DLQ management via WebSocket
- **Manual retry / discard** controls for failed items

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Task queue | Celery + RabbitMQ |
| Cache / pub-sub | Redis |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| Frontend | Vanilla HTML/CSS/JS |
| Infrastructure | Docker + Docker Compose |

## Quick Start

**Prerequisites:** Docker and Docker Compose.

```bash
git clone <repo-url>
cd dlq-manager
docker-compose up
```

This starts all services:

| Service | URL |
|---|---|
| API + Dashboard | http://localhost:8000 |
| Dashboard UI | http://localhost:8000/dashboard |
| RabbitMQ Management | http://localhost:15672 (guest / guest) |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## Configuration

Copy `.env` and fill in your values:

```env
DATABASE_URL=postgresql://user:password@db:5432/webhookdb
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
REDIS_URL=redis://redis:6379
WEBHOOK_SECRET=your-secret-key
```

`WEBHOOK_SECRET` is used to verify the `X-Zapier-Signature` header on incoming webhooks.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest/{source}` | Ingest a webhook from an external source |
| `GET` | `/dlq_items` | List all failed DLQ items |
| `POST` | `/dlq/{id}/retry` | Manually retry a failed item |
| `DELETE` | `/dlq/{id}` | Discard a failed item |
| `GET` | `/dashboard` | Dashboard UI |
| `WS` | `/ws` | Real-time event stream |

### Sending a webhook

```bash
curl -X POST http://localhost:8000/ingest/zapier \
  -H "X-Zapier-Signature: sha256=<hmac_hex>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "action": "create"}'
```

Returns `202 Accepted` on a valid signature, `400` otherwise.

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Local Development (without Docker)

```bash
pip install -r requirements.txt
export $(cat .env | xargs)

# Terminal 1 — API server
uvicorn app.main:app --reload

# Terminal 2 — Celery worker
celery -A app.tasks worker --loglevel=info
```

## How It Works

1. A POST to `/ingest/{source}` verifies the HMAC signature and enqueues a Celery task.
2. The worker attempts to process the event. On failure it retries up to 3 times with exponential backoff (`2^n` seconds).
3. After all retries are exhausted the event is written to the DLQ table.
4. The dashboard receives live updates over WebSocket (backed by Redis pub/sub) and lets operators retry or discard failed items.

## Code Provenance

Except for the frontend (HTML/CSS/JS), all code in this repository was written without the use of large language models or AI code generation tools. This codebase represents hand-written, human-authored software.
