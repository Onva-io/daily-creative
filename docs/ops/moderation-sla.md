# Moderation SLA and Report Triage

## Commitment

Act on user reports of objectionable content **within 24 hours** of receipt. Prefer earlier action when the content is clearly prohibited (CSAM, threats, hate, sexual content involving minors).

## Intake

1. New reports fire the `NewContentReport` webhook alert when `ALERT_WEBHOOK_URL` is set.
2. Medium-confidence automated filter hits fire `ContentQueuedForReview` and appear in `GET /internal/moderation/review-queue`.
3. List open reports: `GET /internal/moderation/reports` with `X-Moderation-Token`.

## Triage steps

1. Inspect the target: `GET /internal/moderation/targets/{target_type}/{target_id}`.
2. For clear violations: hide or remove the submission/reflection, and suspend the user when warranted.
3. Resolve the report with notes: `POST /internal/moderation/reports/{report_id}/resolve`.
4. For filter-queued items: either remove/hide the content or dismiss the queue item after review.

## Escalation

- Suspected CSAM or imminent harm: remove content, suspend account, preserve evidence, and escalate to legal/law enforcement as required.
- If the queue is aging past 12 hours, page the on-call operator.
- If volume exceeds capacity, temporarily tighten automated thresholds (provider config) and document the change.

## Significant policy changes

Publishing a policy document with `is_significant_change=true` requires notifying Apple (and other app stores) **before** users continue under the new terms, so parental consent can be refreshed where required. Follow App Store Connect / Declared Age Range significant-change guidance, then publish.
