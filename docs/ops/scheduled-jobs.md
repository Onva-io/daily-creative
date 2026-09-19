# Scheduled Jobs

Provider cron examples (UTC):

| Job | Schedule | Command |
| --- | --- | --- |
| Account deletion finalize | `0 * * * *` | `python -m app.jobs.account_deletion` |
| Upload cleanup | `15 * * * *` | `python -m app.jobs.upload_cleanup` |
| Session cleanup (all creative types) | `30 * * * *` | `python -m app.jobs.session_cleanup` |
| Idempotency cleanup | `45 * * * *` | `python -m app.jobs.idempotency_cleanup` |
| Deleted media cleanup | `0 3 * * *` | `python -m app.jobs.deleted_media_cleanup` |
| Missing prompt check | `0 12 * * *` | `python -m app.jobs.missing_prompt_check` (ensures today + tomorrow) |

## Railway (current deploy)

[`.github/workflows/scheduled-jobs.yml`](../../.github/workflows/scheduled-jobs.yml) runs every hour on `main` via `railway run`. Set repository secrets:

- `RAILWAY_TOKEN` (required)
- `RAILWAY_PROJECT_ID` (recommended)
- `RAILWAY_SERVICE` (API service name, optional if the token’s default service is the API)
- `RAILWAY_ENVIRONMENT` (optional; defaults to the project’s production environment)

Until `RAILWAY_TOKEN` is set, the workflow checks out and exits without failing. Trigger **Run workflow** on the Actions tab to verify once secrets exist.

AWS EventBridge schedules remain in Terraform for a future AWS cutover.

Dry-run locally:

```bash
make jobs-dry-run
```

Jobs are idempotent and safe under duplicate execution.
