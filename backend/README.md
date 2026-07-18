# Daily Sketch backend

FastAPI application for Daily Sketch. See the repository root README for local setup.

## Phase 1 foundations

- **Settings:** Typed configuration via `app.core.settings` (`APP_ENV`, database, storage, Descope placeholders, `RELEASE_VERSION`, `COMMIT_SHA`, `REQUEST_TIMEOUT_SECONDS`, `PROMPT_DATE_TIMEZONE=UTC`).
- **Request ID:** `RequestIDMiddleware` reads or generates `X-Request-ID` and returns it on every response.
- **Errors:** Domain `AppError` and framework exceptions render the shared OpenAPI `Error` envelope.
- **Logging:** Structured JSON logs include request ID, route, method, status, latency, environment, and release version.
- **Clock:** Injectable `Clock` / `SystemClock` (UTC) for Prompt Date and later domain timing.
- **Storage:** `StorageAdapter` protocol with a Phase 1 `NotConfiguredStorageAdapter` stub. Signed uploads arrive in Phase 7.
- **Routing:** Health probes at `/health/*`. Versioned feature mount at `/api/v1` (empty until Phase 2).

## Useful commands

```bash
make backend-install
make backend-run
make backend-test
make backend-lint
make backend-typecheck
make db-migrate
```
