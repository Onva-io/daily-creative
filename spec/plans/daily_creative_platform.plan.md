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

Everything under `ios/DailyCreative/` is shared and compiled into every app.
An app target contributes only its module, entry point and resources.

1. Create `ios/Daily{Type}/` with:
   - `Daily{Type}App.swift` — `AppDependencies.live(module: {Type}Module())`
     inside `CreativeAppRootView` (copy `DailyStoryApp.swift`; it is ~15 lines).
   - `{Type}Module.swift` conforming to `CreativeModule`: `creativeTypeID`,
     `vocabulary`, `sessionLabels`, `defaultTimerOption`, `makeHomeView()`,
     `makeGuestDraftCard(dependencies:)`.
   - `Resources/` (Info.plist, entitlements, assets, PrivacyInfo.xcprivacy).
2. Image-based types compose `CaptureModuleSupport` (timer → capture → review →
   publish) and supply a `CaptureContentPlugin`. The plugin owns everything the
   type adds to an image: it receives the `CapturedImage` (normalised JPEG plus
   the picker's original bytes for metadata), returns a
   `CaptureExtrasControlling` per review session that renders an optional
   editor under the caption, persists its state as the opaque
   `LocalDraft.contentExtras`, and builds the `PublicationContent`. Sketch uses
   `SketchCapturePlugin` (nothing extra); Photo uses `PhotoCapturePlugin`
   (location). Other flows write a `{Type}FlowViewModel` on top of
   `TimedSessionViewModel` and a home view built from `HomeSections` +
   `HomeViewModel.make(dependencies:)`.
3. Add one target in `ios/project.yml` with `templates: [CreativeApp]`, the
   branding settings (`APP_BUNDLE_ID_BASE`, `BRAND_NAME`, `CREATIVE_TYPE_ID`,
   `COMMUNITY_TITLE`, `START_ACTION_TITLE`, `REQUIRES_CAMERA`,
   `DAILY_REMINDER_NOTIFICATION_ID`), its app group, and any usage-description
   keys. Add four schemes with `templates: [CreativeAppScheme]`.
   Environment xcconfigs in `ios/Config/Environments/` are shared; do not add
   per-app copies.
4. Add one `case` to `SubmissionContentModel` (+ `FeedMapping.mapContent`),
   one to `PublicationContent` (+ `PublicationRepository.createPublication`),
   and one branch to `SubmissionContentView` for the new `content` shape.
5. Type-only logic gets its own `Daily{Type}Tests` unit-test target hosted by
   the new app (see `DailyPhotoTests`); shared-shell tests stay in
   `DailySketchTests`.
6. No `#if PRODUCT_*` or `creativeType ==` checks in `ios/DailyCreative/`.

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
