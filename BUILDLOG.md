# BUILDLOG

## Purpose
This file records the implementation process and the role of AI assistance during the capstone.

## Development log

### 1. Core platform
- Implemented authenticated widget management with create, list, get, update, and delete operations.
- Added tenant ownership to widgets and enforced tenant-scoped queries.
- Implemented public widget configuration and embed snippet generation.
- Added versioned JavaScript delivery at `/public/widget/v1/widget.js`.

### 2. Public submissions
- Added public lead submission endpoint.
- Added payload limits, honeypot spam protection, rate limiting, and idempotency keys.
- Added IP capture and geo enrichment with a provider fallback chain.

### 3. Reliable side effects
- Added durable `notification_jobs` records in the same transaction as submissions.
- Added a background worker with claim/processing states, retry handling, exponential backoff, permanent failure state, and stale-job recovery.
- Kept submission acceptance independent from notification delivery success.

### 4. Dashboard and delivery evidence
- Added authenticated owner dashboard APIs for submission listing, time-based counts, and geo breakdown.
- Added cache headers to widget configuration and versioned JavaScript delivery.
- Added a second-origin demo page for cross-origin widget verification.
- Added `capstone.yaml` evaluator manifest and this build log.

## AI-assisted development
AI assistance was used for implementation planning, code generation/refactoring, debugging, test design, documentation structure, and reviewing edge cases. The final implementation was manually reviewed and verified with the automated test suite and Docker-based runtime checks.

## Important engineering decisions
- Database writes for a submission and its notification job are atomic.
- External notification delivery happens outside the request transaction.
- Notification delivery is intentionally at-least-once; the notification job ID is exposed to downstream receivers so they can implement deduplication.
- Geo enrichment is best-effort and never blocks persistence when external providers fail.
- Dashboard queries always scope data through the authenticated user's tenant.
