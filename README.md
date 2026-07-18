# Daily Sketch

Native iOS creative journal with a FastAPI backend. Every user receives the same three-word Daily Prompt; guests can sketch before authenticating.

This repository is a monorepo. Phase 0 establishes tooling and a local environment only.

## Prerequisites

- Python 3.14
- [uv](https://github.com/astral-sh/uv)
- Docker and Docker Compose
- Xcode 16+ with an iOS 18 simulator
- [XcodeGen](https://github.com/yonaskolb/XcodeGen)
- Node.js / npx (OpenAPI Swift client generation)
- Make

## Quick start

```bash
cp .env.example .env
make backend-install
make up
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
make db-migrate
```

Generate and open the iOS project:

```bash
make ios-generate
open ios/DailySketch.xcodeproj
```

Or build from the CLI:

```bash
make ios-build
```

## Repository layout

| Path | Purpose |
| --- | --- |
| `api/openapi/` | OpenAPI contract (source of truth) |
| `api/generated/` | Generated Swift client — do not edit by hand |
| `backend/` | FastAPI application, Alembic migrations, tests |
| `ios/` | SwiftUI app (`DailySketch`) |
| `spec/` | Product, design, architecture, implementation, infrastructure |

## Make targets

| Target | Description |
| --- | --- |
| `make up` / `down` / `logs` | Local Docker Compose services |
| `make backend-install` | Create Python 3.14 venv and install deps |
| `make backend-run` | Run API with reload on `:8000` |
| `make backend-test` / `lint` / `typecheck` | Backend quality gates |
| `make db-migrate` / `db-reset` | Alembic migrate (reset destroys local volume) |
| `make seed` | No-op in Phase 0 |
| `make api-validate` | Validate OpenAPI |
| `make api-generate-ios` | Regenerate Swift client |
| `make api-check-generated` | Fail if generated client is stale |
| `make repo-checks` | Spec presence, migration names, large-file policy |
| `make docker-build` | Build backend image |
| `make ios-generate` / `ios-build` / `ios-test` | XcodeGen + simulator |
| `make clean-local` | Remove Compose volumes and local caches |

## Local services

Docker Compose provides:

- PostgreSQL 18 on `localhost:5432`
- MinIO on `localhost:9000` (console `:9001`)
- Backend API on `localhost:8000`

Credentials are local placeholders only — see `.env.example`. Never commit real Descope, database, or storage secrets.

## iOS configuration

- Display name: **Daily Sketch**
- Module: `DailySketch`
- Minimum iOS: **18.0**
- Bundle ID placeholder: `com.example.dailysketch.dev`
- Apple Team ID is not committed; set `DEVELOPMENT_TEAM` locally when needed

## OpenAPI workflow

```bash
make api-validate
make api-generate-ios
make api-check-generated
```

CI fails when generated clients drift from `api/openapi/openapi.yaml`.

## Specs

Authoritative documents live in `spec/`. Architectural decisions for Phase 0 are recorded under `spec/decisions/`.
