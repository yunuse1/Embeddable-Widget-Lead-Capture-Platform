# Design Summary

## Data model

The platform is multi-tenant. A `Tenant` owns users and widgets. Each `Widget` belongs to exactly one tenant and has a stable public ID plus configurable fields and display options. Each `Submission` belongs to a widget and stores submitted JSON data, request metadata, and optional geo enrichment. A `NotificationJob` belongs to a submission and provides durable asynchronous side-effect processing with retry state.

## Embed flow

1. An authenticated owner creates/configures a widget.
2. The owner requests `/public/widgets/{public_id}/embed` and receives an embeddable `<script>` snippet.
3. A customer page loads `/public/widget/v1/widget.js` from the API origin.
4. The script requests the public widget configuration, renders the configured form, and submits leads to the public submission endpoint.
5. CORS allows the customer origin to communicate with the API.

## API contract

- Authenticated widget management: `POST/GET /widgets`, `PATCH/DELETE /widgets/{widget_id}`.
- Public configuration: `GET /public/widgets/{public_id}/config`.
- Embed snippet: `GET /public/widgets/{public_id}/embed`.
- Versioned widget asset: `GET /public/widget/v1/widget.js`.
- Public lead capture: `POST /public/widgets/{public_id}/submissions`.
- Owner analytics: `GET /dashboard/submissions`, `/dashboard/stats`, `/dashboard/geo`.

Submission persistence and notification enqueueing are committed together. The notification worker performs webhook delivery asynchronously, retries failures with exponential backoff, and recovers stale processing jobs.

## Non-goal

This version does not provide a production-grade multi-provider email delivery service or a full visual dashboard frontend. The backend dashboard APIs provide the owner analytics contract; external webhook delivery is intentionally implemented as the durable side-effect example.
