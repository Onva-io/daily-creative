# Operational Runbooks

Condensed from `spec/infrastructure.md` §40.

## Backend unavailable

**Symptoms:** `/health/ready` 503, elevated 5xx.
**Checks:** container logs, database connectivity, storage ping, recent deploy.
**Mitigation:** rollback previous image; scale/restart instances.
**Escalation:** on-call engineer.
**Recovery:** verify smoke tests; monitor metrics 30 minutes.

## Database connection failure

**Checks:** managed DB status, connection pool exhaustion, credentials rotation.
**Mitigation:** reduce traffic, restart app, increase pool only after measurement.

## Backup failure

**Mitigation:** retry backup job; block production migration until backup succeeds.

## Storage failure

**Checks:** bucket policy, credentials, head_bucket/ping.
**Mitigation:** fail readiness; disable uploads if necessary.

## Upload spike / image processing failures

**Checks:** upload error rate, CPU, timeout metrics.
**Mitigation:** tighten rate limits temporarily; investigate corrupt uploads.

## Missing Daily Prompt

**Checks:** `make job-missing-prompt-check`; prompt seed coverage.
**Mitigation:** the job and `GET /api/v1/prompts/today` both call `ensure_published` (deterministic create). Re-run the job; if a draft/withdrawn row blocks the date, publish or remove it; `make seed` for bulk future coverage.

## Migration failure

**Mitigation:** stop deploy; assess forward-fix migration; restore only under incident process.

## Account deletion backlog

**Checks:** pending deletion count; run `make account-deletion-finalize`.

## Moderation incident

**Auth:** Descope admin Bearer JWT (`DESCOPE_ADMIN_ROLE`, default `admin`) **or** `X-Moderation-Token`. See [`docs/ops/moderation-sla.md`](moderation-sla.md) for role grant steps.
**Checks:** report queue via `GET /internal/moderation/reports`; automated filter queue via `GET /internal/moderation/review-queue`; approve/reject queue items; approve false-positive reports; redact captions; suspend/remove as needed.
**SLA:** act on reports within **24 hours**. See [`docs/ops/moderation-sla.md`](moderation-sla.md).
**Alerts:** `NewContentReport`, `ContentQueuedForReview` when `ALERT_WEBHOOK_URL` is configured.

## Consent gate inactive / no published policies

**Symptoms:** first-time sign-in never shows the consent gate; no date of birth is requested; `/api/v1/policies/{kind}/html` returns 404, breaking App Store legal links.
**Checks:** `GET /api/v1/policies/current` returns an empty `documents` array. Consent is derived entirely from published documents, so an environment with none reports `consent_required: false` for every user.
**Mitigation:** `scripts/start.sh` runs `python -m app.seeds.policies --bootstrap` on every boot, which publishes the seed set for any kind with nothing published. Redeploy, or run it manually with `railway run uv run python -m app.seeds.policies --bootstrap`. Confirm `POLICY_BOOTSTRAP_ENABLED` is not set to false.
**Alerts:** `Policy bootstrap failed` when `ALERT_WEBHOOK_URL` is configured. Bootstrap is deliberately non-fatal, so the API still serves traffic while degraded.

## Significant policy publish

**Checks:** operator publish with `is_significant_change=true` emits a webhook warning.
**Mitigation:** notify Apple (and other app stores) **before** users continue, then publish. See moderation-sla.md.
**Note:** bootstrap never republishes a kind that already has a live version. Bumping a version in `app/seeds/policies.py` only leaves a draft, so going live stays a deliberate operator action via `POST /internal/moderation/policies/{id}/publish`.

## Credential exposure

**Mitigation:** rotate Descope, DB, storage, moderation tokens; invalidate CI secrets.

## iOS/backend contract mismatch

**Checks:** OpenAPI drift CI; `/health/version` vs iOS build settings.
**Mitigation:** ship compatible client or roll back backend.
