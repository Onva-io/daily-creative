# Alert Catalog

Delivery uses optional `ALERT_WEBHOOK_URL`. Without it, alerts are logged only.

| Alert | Symptom | Check |
| --- | --- | --- |
| BackendDown | `/health/ready` failing | Logs, DB, storage ping |
| Elevated5xx | Error rate sustained | `/metrics`, Sentry |
| LatencyRegression | p95 above architecture targets | `perf-profile`, `/metrics` |
| DatabaseUnavailable | ready check database=unavailable | Provider status, pool |
| BackupFailure | backup job/script failed | Backup logs |
| MigrationFailure | Alembic upgrade error | Migration logs |
| StorageFailure | ready check storage=unavailable | Bucket credentials/policy |
| UploadFailureSpike | upload 4xx/5xx increase | Upload metrics |
| MissingPrompt | missing_prompt_check failed | Prompt table, seed |
| JobFailure | job outcome error counter | Job logs |
| AuthFailureSpike | auth failure counter | Descope/JWT config |
| NewContentReport | user submitted a report | `/internal/moderation/reports`, act within 24h |
| ContentQueuedForReview | medium-confidence filter hit | `/internal/moderation/review-queue` |
| SignificantPolicyChange | operator publishing significant policy | notify app stores before users continue |

Configure provider paging (PagerDuty/Opsgenie/etc.) to consume the webhook in staging/production.
