# Embeddable Widget & Lead Capture Platform

A backend platform for embedding lead-capture forms into websites and processing submissions safely. The API stores each lead first, then creates a durable notification job for an asynchronous webhook side effect.

## What it demonstrates

- Embeddable widget-oriented public submission API
- PostgreSQL persistence with SQLAlchemy and Alembic
- Request validation and payload limits
- IP-based submission rate limiting
- Optional IP geolocation enrichment
- `Idempotency-Key` support for safe retries and duplicate requests
- Atomic creation of a submission and its notification job
- Background webhook delivery with retries and exponential backoff
- Durable job state: `pending`, `processing`, `processed`, `failed`
- Stale `processing` job recovery after worker interruption
- Worker-level protection against reprocessing completed jobs
- Dockerized API, PostgreSQL, and notification worker
- Automated tests in GitHub Actions

## Architecture

```text
Browser / Embedded Widget
          |
          | POST /public/widgets/{public_id}/submissions
          v
+-------------------------+
| FastAPI application     |
| - validation             |
| - rate limiting          |
| - idempotency            |
| - geo enrichment        |
+------------+------------+
             |
             | one DB transaction
             v
+-------------------------+
| PostgreSQL              |
| submissions             |
| notification_jobs       |
+------------+------------+
             |
             | claim pending job
             v
+-------------------------+
| Notification Worker     |
| - claim with row lock   |
| - webhook delivery      |
| - retry/backoff          |
| - stale recovery        |
+------------+------------+
             |
             v
       External Webhook
```

The key reliability boundary is the database transaction: a lead submission is committed together with its notification job. The external webhook is never called from the request transaction, so a webhook outage does not make the lead submission fail.

## Submission flow

1. Client sends a submission.
2. API validates payload size, field count, field lengths, and honeypot.
3. If an `Idempotency-Key` was already used for the same widget, the existing submission is returned.
4. Otherwise the submission is inserted.
5. A `notification_jobs` row is created in the same transaction.
6. The transaction commits and the API returns `201 Accepted`.
7. The worker later claims the job and attempts the webhook.

## Idempotency

Clients can send:

```http
Idempotency-Key: checkout-123
```

The key is unique per widget. Repeating the same request returns the original submission ID and does not create another notification job. A database uniqueness constraint also protects against concurrent duplicate requests.

## Notification reliability

Jobs start as `pending` and are claimed with a database row lock. During delivery they become `processing`.

Transient delivery failures return the job to `pending` with exponential backoff:

```text
attempt 1 -> 5 seconds
attempt 2 -> 10 seconds
attempt 3 -> 20 seconds
attempt 4 -> 40 seconds
attempt 5 -> failed
```

After the maximum number of attempts, the job becomes `failed` and the original submission remains intact.

If a worker crashes while a job is `processing`, the worker can recover jobs whose `processing_started_at` is older than the processing timeout and return them to `pending`.

Delivery is intentionally **at-least-once**. If a worker crashes after the remote webhook accepts a request but before the local job is marked `processed`, the webhook can be attempted again. Each request includes `X-Notification-Job-Id` so a receiver can implement its own idempotent deduplication.

## API

Health check:

```http
GET /health
```

Public submission:

```http
POST /public/widgets/{public_id}/submissions
Content-Type: application/json
Idempotency-Key: checkout-123

{
  "data": {
    "email": "lead@example.com",
    "name": "Test Lead"
  },
  "honeypot": ""
}
```

A successful submission returns a stable submission ID with status `accepted`. Notification delivery happens asynchronously.

## Local setup

### 1. Configure environment

Copy `.env.example` to `.env` and configure:

```text
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lead_capture
NOTIFICATION_WEBHOOK_URL=https://example.com/webhook
```

### 2. Install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

### 5. Start the notification worker

In a second terminal:

```bash
python -m app.services.notification_worker
```

## Docker

The repository includes a Dockerfile and Compose setup for PostgreSQL, the API, and the notification worker.

```bash
docker compose up --build
```

The API is available on port `8000` and PostgreSQL on port `5432`.

Before production use, run the Alembic migrations against the configured database.

## Testing

Run the full test suite with:

```bash
python -m pytest -q
```

The test suite covers submission idempotency, notification job creation, worker claiming, successful delivery, retry behavior, permanent failure after maximum attempts, completed-job protection, and stale processing recovery.

GitHub Actions runs the tests against PostgreSQL 16.

## Failure scenarios

| Scenario | Result |
|---|---|
| Duplicate client retry | Same submission returned; no duplicate job |
| Webhook unavailable | Submission remains accepted; job retries |
| Repeated webhook failure | Job eventually becomes `failed`; submission remains intact |
| Worker crashes while processing | Stale job is recovered and retried |
| Completed job invoked again | External delivery is not triggered again |
| Remote accepts request before worker crash | Possible duplicate delivery; receiver should dedupe by job ID |

## Security and operational notes

- Payload size and field limits reduce abuse and accidental oversized requests.
- Submission rate limiting is applied per widget and client IP.
- `Idempotency-Key` is scoped to the widget.
- External webhook calls have a finite timeout.
- Secrets are supplied through environment variables rather than committed configuration.
- The example Docker configuration is intended for development; production deployments should add proper secrets management, TLS, restrictive CORS, observability, and infrastructure-level resource limits.

## Project structure

```text
app/
├── models/
│   ├── submission.py
│   └── notification_job.py
├── routers/
│   └── submissions.py
├── services/
│   └── notification_worker.py
├── config.py
├── database.py
└── main.py
migrations/
tests/
Dockerfile
docker-compose.yaml
```

## Status

This project is a capstone demonstrating reliable side-effect handling for an embeddable lead-capture backend. The core design goal is simple: **never lose a lead because an external notification service is temporarily unavailable.**
