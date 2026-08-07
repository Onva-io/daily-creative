# Moderation SLA and Report Triage

## Commitment

Act on user reports of objectionable content **within 24 hours** of receipt. Prefer earlier action when the content is clearly prohibited (CSAM, threats, hate, sexual content involving minors).

## Authorisation

Moderation endpoints under `/internal/moderation/*` accept **either**:

1. **Descope admin Bearer JWT** — session token for a local user with status `active` who has the project-level Descope role configured by `DESCOPE_ADMIN_ROLE` (default `admin`). Audit rows use `user:<uuid>` and populate `reports.reviewed_by_user_id`.
2. **Shared operator token** — header `X-Moderation-Token: $MODERATION_OPERATOR_TOKEN` for break-glass / automation. Audit rows use `token:operator`; `reviewed_by_user_id` stays null.

### Granting the admin role (Descope console)

1. Open the Descope project → **Authorization** → **RBAC**.
2. Create a project-level permission/role named to match `DESCOPE_ADMIN_ROLE` (default `admin`) if it does not exist.
3. Assign that role to each operator user.
4. Operators sign in via the normal app/auth flow; their next session JWT includes `roles: ["admin"]`.

Revoke access by removing the role in Descope (effective on the next session refresh).

## Intake

1. New reports fire the `NewContentReport` webhook alert when `ALERT_WEBHOOK_URL` is set.
2. Medium-confidence automated filter hits fire `ContentQueuedForReview` and appear in `GET /internal/moderation/review-queue` (includes a text/caption `preview`).
3. List open reports: `GET /internal/moderation/reports`.

## Triage steps

1. Inspect the target: `GET /internal/moderation/targets/{target_type}/{target_id}`.
2. For clear violations: hide or remove the submission/reflection, and suspend the user when warranted.
3. For reported content that is **not** a violation: `POST /internal/moderation/reports/{report_id}/approve` (restores the target if hidden/removed and dismisses the report).
4. Otherwise resolve with notes: `POST /internal/moderation/reports/{report_id}/resolve`.
5. For filter-queued items:
   - Approve (keep published): `POST /internal/moderation/review-queue/{item_id}/approve`
   - Reject (hide by default, or remove with `"remove": true`): `POST /internal/moderation/review-queue/{item_id}/reject`
6. Caption-only issues: `POST /internal/moderation/submissions/{id}/redact-caption` (clears caption, leaves the submission published).

## Escalation

- Suspected CSAM or imminent harm: remove content, suspend account, preserve evidence, and escalate to legal/law enforcement as required.
- If the queue is aging past 12 hours, page the on-call operator.
- If volume exceeds capacity, temporarily tighten automated thresholds (provider config) and document the change.

## Significant policy changes

Publishing a policy document with `is_significant_change=true` requires notifying Apple (and other app stores) **before** users continue under the new terms, so parental consent can be refreshed where required. Follow App Store Connect / Declared Age Range significant-change guidance, then publish.
