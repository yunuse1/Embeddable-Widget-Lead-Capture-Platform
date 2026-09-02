# Embeddable Widget & Lead Capture Platform

A multi-tenant backend platform for embedding lead-capture widgets into external websites and processing submissions safely. Owners authenticate to manage widgets, while public widget endpoints expose configuration, an embed snippet, and versioned JavaScript delivery.

## What it demonstrates

- Authenticated widget CRUD
- Multi-tenant isolation for widget and submission data
- Embeddable widget config and snippet generation
- Versioned `widget.js` delivery with cache headers
- Cross-origin submission support through CORS
- Public lead submission API
- PostgreSQL persistence with SQLAlchemy and Alembic
- Request validation, payload limits, honeypot spam protection, and rate limiting
- IP-based geo enrichment with provider fallback
- `Idempotency-Key` support for safe retries and duplicate requests
- Atomic creation of a submission and its notification job
- Background webhook delivery with retries and exponential backoff
- Durable job state: `pending`, `processing`, `processed`, `failed`
- Stale `processing` job recovery after worker interruption
- Authenticated owner dashboard APIs for submissions, time-based counts, and geo breakdown
- Dockerized API, PostgreSQL, and notification worker
- Automated tests in GitHub Actions

## Architecture

```text
External Website / Embedded Widget
              |
              | cross-origin GET config + POST submission
              v
+-----------------------------+
| FastAPI application         |
| - authenticated widget CRUD |
| - tenant isolation          |
| - public widget delivery    |
| - validation/rate limiting  |
| - idempotency + geo         |
+---------------+-------------+
                |
                | one DB transaction
                v
+-----------------------------+
| PostgreSQL                  |
| tenants / users / widgets   |
| submissions / notification_jobs |
+---------------+-------------+
                |
                | claim pending job
                v
+-----------------------------+
| Notification Worker         |
| - row-lock claim             |
| - webhook delivery           |
| - retry/backoff              |
| - stale recovery             |
+---------------+-------------+
                |
                v
         External Webhook

Authenticated Owner
        |
        +--> /widgets
        +--> /dashboard/submissions
        +--> /dashboard/stats
        +--> /dashboard/geo
```

The reliability boundary is the database transaction: a lead submission is committed together with its notification job. External delivery is asynchronous, so a webhook outage does not make the lead submission fail.

## Widget management

Authenticated owners can:

```text
POST   /widgets
GET    /widgets
GET    /widgets/{widget_id}
PATCH  /widgets/{widget_id}
DELETE /widgets/{widget_id}
```

Every widget query is scoped to the authenticated user's `tenant_id`, preventing one tenant from accessing another tenant's widgets.

## Embedding

For an active public widget:

```text
GET /public/widgets/{public_id}/config
GET /public/widgets/{public_id}/embed
GET /public/widget/v1/widget.js
```

The embed endpoint returns a ready-to-copy snippet. The JavaScript bundle is versioned under `v1` and uses the widget public ID to load configuration from the API origin.

The config endpoint uses a short public cache policy and the JavaScript bundle uses a longer cache policy:

```text
config:   Cache-Control: public, max-age=300, must-revalidate
widget.js: Cache-Control: public, max-age=3600
```

## Cross-origin verification

`demo/second-origin.html` is a simple page intended to be served from a different port/origin than the API. Replace `REPLACE_WITH_PUBLIC_WIDGET_ID` with an active public widget ID, then serve the `demo/` directory with a static server, for example:

```bash
python -m http.server 5500 --directory demo
```

Open `http://localhost:5500/second-origin.html` while the API is running on port `8000`. The widget script and config request are therefore cross-origin requests and are covered by the API's CORS configuration.

## Submission flow

1. Client sends a submission.
2. API validates payload size, field count, field lengths, and honeypot.
3. If an `Idempotency-Key` was already used for the same widget, the existing submission is returned.
4. The API performs best-effort geo enrichment using a provider fallback chain.
5. The submission is inserted.
6. A `notification_jobs` row is created in the same transaction.
7. The transaction commits and the API returns `201`.
8. The worker later claims the job and attempts the webhook.

## Geo fallback

The enrichment chain is:

```text
ip-api.com
     |
     | failure / invalid response
     v
ipapi.co
     |
     | failure
     v
empty geo result
```

Geo enrichment is best-effort: provider failures never prevent the submission from being persisted.

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

If a worker crashes while a job is `processing`, stale jobs are returned to `pending` after the processing timeout.

Delivery is intentionally **at-least-once**. If a worker crashes after the remote webhook accepts a request but before the local job is marked `processed`, the webhook can be attempted again. Each request includes `X-Notification-Job-Id` so a receiver can implement deduplication.

## Owner dashboard

Authenticated owners can inspect tenant-scoped data through:

```text
GET /dashboard/submissions?limit=50&offset=0
GET /dashboard/stats?days=30
GET /dashboard/geo?days=30
```

The dashboard APIs provide:

- paginated submission listing
- total submission count
- daily submission counts for a selected period
- country/city geo breakdown

All dashboard queries are filtered through the authenticated user's tenant.

## API example

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

The repository includes a Dockerfile and Compose setup for PostgreSQL, the API, database migrations, and the notification worker.

```bash
docker compose up --build
```

The API is available on port `8000` and PostgreSQL on port `5432`.

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
| Geo provider unavailable | Submission is still persisted with empty geo fields |
| Tenant A requests Tenant B widget | Widget is not returned by authenticated management API |

## Security and operational notes

- Payload size and field limits reduce abuse and accidental oversized requests.
- Submission rate limiting is applied per widget and client IP.
- `Idempotency-Key` is scoped to the widget.
- External webhook calls have a finite timeout.
- Secrets are supplied through environment variables rather than committed configuration.
- CORS is intentionally open for the embeddable public widget flow; production deployments should restrict origins where appropriate.
- Production deployments should add proper secrets management, TLS, observability, and infrastructure-level resource limits.

## Evaluator artifacts

- `capstone.yaml` — evaluator manifest with run/test commands and endpoint inventory.
- `BUILDLOG.md` — development and AI-assistance log.
- `EVIDENCE.md` — requirement-to-proof summary and reliability evidence.
- `demo/second-origin.html` — cross-origin widget verification page.

## Project structure

```text
app/
├── models/
│   ├── tenant.py
│   ├── widget.py
│   ├── submission.py
│   └── notification_job.py
├── routers/
│   ├── auth.py
│   ├── widgets.py
│   ├── public.py
│   ├── submissions.py
│   └── dashboard.py
├── services/
│   ├── geo.py
│   └── notification_worker.py
├── config.py
├── database.py
└── main.py
demo/
migrations/
tests/
capstone.yaml
BUILDLOG.md
EVIDENCE.md
Dockerfile
docker-compose.yaml
```

## Status

This project demonstrates a multi-tenant embeddable lead-capture platform with authenticated widget management, cross-origin delivery, public submissions, geo enrichment, owner analytics, and reliable asynchronous side effects. The core reliability goal is simple: **never lose a lead because an external notification service is temporarily unavailable.**
