# Implementation Evidence

This document maps the capstone reliability requirements to the implementation and automated tests in this repository.

## 1. Safe side effects

**Requirement:** A notification failure must not cause the lead submission itself to fail.

**Implementation:** The API inserts the `Submission` and its `NotificationJob` in the same database transaction. The external webhook is executed later by the background worker, outside the request path.

**Evidence:** `app/routers/submissions.py` creates the submission, flushes it to obtain its ID, creates a pending notification job, and commits them together. `app/services/notification_worker.py` owns the external webhook call and catches delivery failures.

**Test:** Worker failure tests verify that delivery can fail while the submission remains intact.

---

## 2. Durable background jobs

**Requirement:** Side effects should survive the end of the HTTP request and be processed asynchronously.

**Implementation:** `notification_jobs` is a PostgreSQL-backed table linked to `submissions`. Jobs have explicit lifecycle states and timestamps.

**Evidence:** `NotificationJob` stores `pending`, `processing`, `processed`, and `failed` state, retry attempts, availability time, errors, and processing timestamps.

**Test:** Worker tests cover claiming and processing pending jobs.

---

## 3. Idempotent submission handling

**Requirement:** Client retries must not create duplicate leads or duplicate notification jobs.

**Implementation:** `Idempotency-Key` is scoped to the widget and protected by a database uniqueness constraint on `(widget_id, idempotency_key)`. The API also handles a concurrent uniqueness conflict safely.

**Evidence:** `Submission` defines the unique constraint; `create_submission` checks for an existing submission before inserting and handles `IntegrityError` for concurrent requests.

**Test:** `tests/test_submission_idempotency.py` verifies two requests with the same key return the same submission ID and create exactly one submission and one notification job.

---

## 4. Retry and exponential backoff

**Requirement:** Temporary webhook failures should be retried without blocking the lead submission.

**Implementation:** Failed jobs increment `attempts`, remain `pending`, and receive an exponentially increasing `available_at` delay. After five attempts the job becomes permanently `failed`.

**Backoff policy:**

```text
attempt 1 -> 5s
attempt 2 -> 10s
attempt 3 -> 20s
attempt 4 -> 40s
attempt 5 -> failed
```

**Test:** Worker tests cover retry behavior and permanent failure after `MAX_ATTEMPTS`.

---

## 5. Worker crash / stale processing recovery

**Requirement:** A job must not remain permanently stuck if a worker stops while processing it.

**Implementation:** Claimed jobs receive `processing_started_at`. Jobs that remain in `processing` longer than the configured processing timeout are reset to `pending` and made immediately available for another attempt.

**Evidence:** `NotificationJob.processing_started_at` plus the worker's stale-job recovery logic.

**Test:** `tests/test_notification_worker.py` covers stale processing recovery.

---

## 6. At-least-once delivery and duplicate protection

**Requirement:** The system should explicitly define what happens around worker crashes and external side effects.

**Implementation:** Delivery is at-least-once. If a worker crashes after a remote receiver accepts the request but before the local job is marked `processed`, the job can be retried.

**Deduplication mechanism:** Every webhook request includes `X-Notification-Job-Id`. A downstream receiver can use this stable job ID to make its own operation idempotent.

**Trade-off:** Exactly-once delivery cannot be guaranteed across an independent external service and a local database without a shared transactional boundary. The system therefore favors durability of the lead and explicit retry semantics.

---

## 7. Completed jobs are not re-delivered

**Requirement:** A successfully completed notification must not be sent again by normal worker processing.

**Implementation:** `process_job` returns immediately for jobs already marked `processed` or `failed`.

**Test:** Worker tests verify that an already processed job does not trigger another webhook call.

---

## 8. Abuse and payload controls

**Requirement:** Public submission endpoints should reject obviously abusive or oversized requests.

**Implementation:** The API enforces:

- maximum request payload size: 32 KB
- maximum fields: 30
- maximum field name length: 100 characters
- maximum string value length: 2,000 characters
- honeypot spam rejection
- per-widget/client-IP rate limiting

**Evidence:** Validation constants and checks are implemented in `app/routers/submissions.py`.

---

## 9. Containerized runtime

**Requirement:** API and background processing should be reproducible in development.

**Implementation:** `Dockerfile` packages the Python application. `docker-compose.yaml` defines PostgreSQL, the API container, and a separate notification worker container. PostgreSQL health checks prevent dependent services from starting before the database is ready.

**Run:**

```bash
docker compose up --build
```

---

## 10. Automated verification

The repository has GitHub Actions CI using Python 3.12 and PostgreSQL 16. The latest README commit was verified by workflow run `33621516333` with conclusion `success`.

The test suite covers:

- submission idempotency
- notification job creation
- worker job claiming
- successful delivery
- retry behavior
- permanent failure
- completed-job protection
- stale processing recovery

## Requirement-to-proof summary

| Requirement | Implementation | Automated proof |
|---|---|---|
| Safe side effect | DB-backed async job | Worker failure tests |
| Durable enqueue | Submission + job transaction | Submission/job tests |
| Idempotency | Unique key + conflict handling | `test_submission_idempotency.py` |
| Retry | Exponential backoff | Worker retry tests |
| Permanent failure | `MAX_ATTEMPTS` | Max-attempt test |
| Crash recovery | `processing_started_at` | Stale recovery test |
| No duplicate completed delivery | Job state guard | Processed-job test |
| Abuse protection | Limits + rate limiter + honeypot | Router validation behavior |
| Reproducible runtime | Docker Compose | API + worker containers |
| CI verification | GitHub Actions + PostgreSQL | Workflow run `33621516333` |

## Final design statement

The central reliability decision is to treat the lead submission as the durable business event and the notification as a recoverable side effect. The API commits the lead even when an external notification system is unavailable. The worker provides retries, backoff, stale-job recovery, and explicit failure state without deleting or invalidating the original lead.
