# Daily Creative Platform — Extension Guide

This document describes how to add a new creative type to the Daily Creative platform.

## Architecture Overview

- **Per-type session tables**: Each creative type has `*_sessions` and `*_session_events` tables.
- **Publication anchor**: `creative_publications` holds shared social/index fields.
- **Typed detail tables**: Each type has a 1:1 detail table (e.g. `sketch_submissions`, `story_submissions`).
- **Shared social layer**: Likes, reflections, and activity events FK to `creative_publications.id`.
- **Registry**: `backend/app/creative_types/` defines per-type metadata and validation.

## Checklist: Adding Creative Type N

### 1. Database migration

1. Add enum value to `creative_type` Postgres enum.
2. Create `{type}_sessions` and `{type}_session_events` tables with type-specific statuses.
3. Create `{type}_submissions` detail table with 1:1 FK to `creative_publications.id`.
4. Register the type in `CreativeTypeRegistry` (`backend/app/creative_types/{type}.py`).

### 2. Backend code

1. Add ORM models for session, session events, and submission detail.
2. Add repository and service (extend `BaseCreativeSessionService` for session lifecycle).
3. Add API routes under `/api/v1/{type}-sessions`.
4. Add submission content schema and register validation in `PublicationService`.
5. Update feed projection join logic in `PublicationRepository`.

### 3. OpenAPI contract

1. Add `{Type}SubmissionContent` schema.
2. Extend `CreateSubmissionRequest.content` discriminator mapping.
3. Add session request/response schemas.
4. Run `make api-generate-ios`.

### 4. iOS app target

1. Add xcconfig files under `ios/Config/Daily{Type}/`.
2. Add app target in `ios/project.yml` with `CREATIVE_TYPE_ID` and branding keys.
3. Add feature module under `ios/Daily{Type}/Features/`.
4. Wire `ProductConfig` strings in plist/xcconfig (no hardcoded type checks in shared code).

### 5. Tests

Mirror the sketch test suite:

- Session lifecycle (create, events, abandon, expiry)
- Publication create/delete
- Feed and profile filtered by `creative_type`
- Cross-type isolation (session from type A cannot publish as type B)

## What should NOT change

When adding a new type, these layers remain unchanged:

- Auth and user accounts
- Likes, reflections, blocks, reports (polymorphic on publication id)
- Daily prompts (shared across types in v1)
- Core feed/social services (only registry join helpers may need a new branch)

## Naming conventions

| Concept | Convention | Example |
|---------|------------|---------|
| Platform | Daily Creative | `dailycreative-backend`, `DailyCreativeAPI` |
| Creative type enum | lowercase slug | `sketch`, `story`, `poetry` |
| App product brand | Daily {Type} | Daily Sketch, Daily Story |
| Session table | `{type}_sessions` | `sketch_sessions` |
| Detail table | `{type}_submissions` | `story_submissions` |
