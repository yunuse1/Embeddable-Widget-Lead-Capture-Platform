# Implementation Evidence

This document maps the capstone reliability requirements and evaluator probes to implementation and automated verification. Manual checks are explicitly marked so no terminal/browser result is claimed before it is actually run.

## Evaluator probe map

| Probe | Expected behavior | Automated evidence | Manual evidence |
|---|---|---|---|
| Probe 1 — valid public submission | Valid lead returns success and is persisted | Existing submission/idempotency/worker test coverage | Run a real POST against a seeded active widget |
| Probe 2 — malformed/oversized payload | Invalid or oversized input returns 4xx | `tests/test_public_submission.py`, `tests/test_spam_honeypot.py` | Send a request whose `Content-Length` exceeds 32 KB |
| Probe 3 — rate limit | Repeated submissions from the same widget/IP eventually return 429 | `tests/test_rate_limit.py` covers limiter behavior | Send 6 rapid public submissions from one client/IP |
| Probe 4 — geo fallback | Provider A failure falls through to provider B; both failures remain non-fatal | `tests/test_geo_fallback.py` | Optional live geo lookup check |
| Probe 5 — durable notification | Lead remains persisted while notification is retried asynchronously | Existing worker/submission tests | Stop/replace webhook receiver and inspect job state |
| Probe 6 — honeypot | Filled honeypot is rejected as spam | `tests/test_spam_honeypot.py` plus endpoint logic | Submit the rendered widget with the hidden honeypot populated |

## 1. Safe side effects

**Requirement:** A notification failure must not cause the lead submission itself to fail.

**Implementation:** The API inserts the `Submission` and its `NotificationJob` in the same database transaction. The external webhook is executed later by the background worker, outside the request path.

**Evidence:** `app/routers/submissions.py` creates the submission, flushes it to obtain its ID, creates a pending notification job, and commits them together. `app/services/notification_worker.py` owns the external webhook call and catches delivery failures.

## 2. Durable background jobs

**Requirement:** Side effects survive the HTTP request and are processed asynchronously.

**Implementation:** `notification_jobs` is PostgreSQL-backed and linked to `submissions`, with explicit lifecycle and retry state.

## 3. Idempotent submission handling

**Requirement:** Client retries must not create duplicate leads or duplicate notification jobs.

**Implementation:** `Idempotency-Key` is scoped to the widget and protected by a database uniqueness constraint on `(widget_id, idempotency_key)`. Concurrent uniqueness conflicts are handled safely.

**Automated proof:** `tests/test_submission_idempotency.py` when present in the repository's existing suite.

## 4. Retry and exponential backoff

Failed jobs increment `attempts`, remain retryable until the maximum attempt count, and receive exponentially increasing `available_at` delays. After five attempts the job becomes `failed`.

## 5. Worker crash / stale processing recovery

Claimed jobs receive `processing_started_at`. Stale processing state is reset so another worker can retry the job.

## 6. At-least-once delivery

Delivery is explicitly at-least-once. A remote receiver can deduplicate using the stable `X-Notification-Job-Id` header. Exactly-once delivery is not claimed across independent database and webhook systems.

## 7. Completed jobs are protected

Normal worker processing skips jobs already marked `processed` or `failed`, preventing routine duplicate delivery.

## 8. Abuse and payload controls

The public endpoint enforces a 32 KB request-size ceiling, maximum 30 fields, maximum 100-character field names, maximum 2,000-character string values, a honeypot field, and per-widget/client-IP rate limiting. The endpoint also supports `Idempotency-Key`.

## 9. Geo enrichment fallback

IP enrichment tries `ip-api.com`, then falls back to `ipapi.co`, and returns an empty geo result if both providers fail.

## 10. Containerized runtime

`docker compose up --build` starts PostgreSQL, migrations, API, and the notification worker.

## 11. Automated verification

Run the canonical capstone command:

```bash
docker compose exec api python -m pytest -q
```

The repository includes focused coverage for public submission validation, rate limiting, honeypot behavior, and geo fallback in addition to the existing reliability tests.

## 12. Screenshot evidence

The repository includes reproducible terminal test evidence in `assets/`:

- [`assets/seed_and_tests.png`](assets/seed_and_tests.png) — seed/setup output and automated test execution evidence.
- [`assets/tests.png`](assets/tests.png) — automated test output evidence.

These screenshots are supporting artifacts only; the authoritative verification remains the test suite itself and the canonical command above.

## Requirement-to-proof summary

| Requirement | Implementation | Automated proof |
|---|---|---|
| Safe side effect | DB-backed async job | Worker failure tests |
| Durable enqueue | Submission + job transaction | Submission/job tests |
| Idempotency | Unique key + conflict handling | Existing idempotency test |
| Retry | Exponential backoff | Worker retry tests |
| Permanent failure | Maximum attempts | Worker max-attempt test |
| Crash recovery | Processing timestamp | Stale recovery test |
| No duplicate completed delivery | Job state guard | Processed-job test |
| Abuse protection | Payload limits + rate limiter + honeypot | `test_public_submission.py`, `test_rate_limit.py`, `test_spam_honeypot.py` |
| Geo fallback | Two-provider fallback | `test_geo_fallback.py` |
| Reproducible runtime | Docker Compose | Canonical Docker/test command |
| Evaluator probes | Probe 1–6 mapping | Automated + clearly marked manual checks |

## Final design statement

The central reliability decision is to treat the lead submission as the durable business event and the notification as a recoverable side effect. The API commits the lead even when an external notification system is unavailable. The worker provides retries, backoff, stale-job recovery, and explicit failure state without deleting or invalidating the original lead.
