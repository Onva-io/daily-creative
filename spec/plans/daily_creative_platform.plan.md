# Daily Creative Platform — Extension Guide

This document describes how to add a new creative type (a new App Store app)
to the Daily Creative platform. The platform is generic; a creative type is a
plugin that contributes its content shape, its session stages, and four
behaviour hooks. Nothing else should need to change.

## Architecture Overview

- **One session table**: `creative_sessions` (+ `creative_session_events`) for
  every type. Generic status (`active|paused|completed|abandoned|expired`);
  type-owned sub-state in `stage`, stage-entry timestamps in `stage_timestamps`.
- **One publication table**: `creative_publications` holds shared fields as
  columns (`caption`, `upload_id`, counts, timestamps) and type-specific fields
  in JSONB `content`, validated and projected by the type's handler.
- **Shared social layer**: Likes, reflections, reports, and activity events FK
  to `creative_publications.id`.
- **Registry**: `backend/app/creative_types/` — each type is one module
  exporting a `CreativeTypeDefinition`. The registry drives request/response
  content unions, session transitions, moderation, redaction, and cleanup.
- **One API surface**: `/api/v1/sessions`, `/api/v1/submissions`,
  `/api/v1/feed/recent`, `/api/v1/users/{username}/submissions`, all filtered by
  `creative_type`. Responses carry a discriminated `content` object.
- **Per-app preferences**: `creative_type_preferences` (timer memory, daily
  reminder). Only timezone, appearance, and profile are account-wide.

## Checklist: Adding Creative Type N

### 1. Backend (one module + two one-liners)

1. Add the enum value to `CreativeType` in `backend/app/models/enums.py` and a
   one-line migration: `ALTER TYPE creative_type ADD VALUE IF NOT EXISTS '{type}'`.
2. Create `backend/app/creative_types/{type}.py` with:
   - `{Type}SubmissionContent(SubmissionContentBase)` — request content with
     `creative_type: Literal["{type}"]`.
   - `{Type}ContentResponse(ContentResponseBase)` — what feed/detail return
     under `content`.
   - `{Type}Handler(CreativeTypeHandler)` — `validate`, `project`, and
     optionally `moderation_texts`, `redact`, `inspect`.
   - `{TYPE}_DEFINITION = CreativeTypeDefinition(...)` declaring
     `post_timer_stage`, `stage_rules`, `abandon_forbidden_stages`,
     `read_expiry_exempt_stages`, `requires_upload`.
3. Register the definition in `_build_registry()`
   (`backend/app/creative_types/registry.py`).

No new tables, services, routes, jobs, or `if creative_type ==` branches.

### 2. OpenAPI contract

1. Add `{type}` to the `CreativeType` enum.
2. Add `{Type}SubmissionContent` and `{Type}Content` schemas and extend the
   `CreateSubmissionRequest.content` and `SubmissionContent` discriminator
   mappings.
3. Document the type's stages/events in `SessionStage` / `SessionEventType`.
4. Run `make api-validate` and `make api-generate-ios`.

### 3. iOS app target

1. Add xcconfig files under `ios/Config/Daily{Type}/`.
2. Add the target in `ios/project.yml` from the `CreativeApp` template with
   `CREATIVE_TYPE_ID` and branding keys.
3. Add `ios/Daily{Type}/{Type}Module.swift` conforming to `CreativeModule`
   (home view, session flow, review content editor, content card renderers).
4. No `#if PRODUCT_*` or `creativeType ==` checks in `ios/DailyCreative/`.

### 4. Tests

- Session: type-specific stage events accepted, other types' rejected.
- Publication create/delete with the new content shape; feed and profile
  filtered by `creative_type`; account deletion redacts via the handler.
- Contract: responses validate against `Submission` / `FeedItem` /
  `CreativeSession` in `api/openapi/openapi.yaml`.

### 5. Docs

- Product spec `spec/product-{type}.md`; privacy notes if the type adds a new
  data class (as Photo did with location).

## What should NOT change

- Auth, accounts, and account deletion flow
- Likes, reflections, blocks, reports (polymorphic on publication id)
- Daily prompts (shared across types)
- Session/publication/feed/moderation/cleanup services (they read the registry)

## Naming conventions

| Concept | Convention | Example |
|---------|------------|---------|
| Platform | Daily Creative | `dailycreative-backend`, `DailyCreativeAPI` |
| Creative type enum | lowercase slug | `sketch`, `story`, `photo` |
| App product brand | Daily {Type} | Daily Sketch, Daily Story, Daily Photo |
| Type module | `backend/app/creative_types/{type}.py` | `photo.py` |
| Stage names | lowercase snake | `ready_for_photo`, `writing` |
