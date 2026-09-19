# 0012 — Unified creative model

- Status: Accepted
- Date: 2026-09-19
- Deciders: Product, Engineering

## Context

Daily Sketch and Daily Story shipped as two App Store apps on one backend, but the backend grew a parallel stack per creative type: `sketch_sessions` / `story_sessions` (+ events) with different status enums, `sketch_submissions` / `story_submissions` detail tables, two session services with near-identical state machines, two API prefixes (`/sketch-sessions`, `/story-sessions`), two cleanup jobs, and `if creative_type == ...` branches in publications, feed projection, moderation, and account deletion. Adding Daily Photo by the same pattern would have meant a third copy of everything, and a dozen apps would be untenable.

The `CreativeTypeRegistry` existed but only held metadata (table names, field lists); it did not drive behaviour.

There is one TestFlight user, so migration risk is low and the cost of carrying the per-type shape forward outweighs the cost of a one-time backfill.

## Decision

Model a creative type as a plugin over a single generic data model. Nothing outside `backend/app/creative_types/{type}.py` branches on the type.

### Data

- `creative_sessions` — one table for every type. Generic `status` (`active|paused|completed|abandoned|expired`); type-owned sub-state in `stage` (text) with stage-entry timestamps in `stage_timestamps` (JSONB). `creative_session_events.event_type` is text validated against the type's declared events.
- `creative_publications` — shared fields as columns (`caption`, `upload_id`, counts, timestamps); type-specific fields in JSONB `content` shaped by the type's content schema. `session_id` is a unique FK to `creative_sessions`.
- Per-type tables and their enums are dropped after backfill (`0004_unified_creative_model`).

### Behaviour

`CreativeTypeDefinition` declares: request content schema, response content schema, `post_timer_stage`, `stage_rules` (event → allowed from-stages → resulting stage → optional timestamp key), `abandon_forbidden_stages`, `read_expiry_exempt_stages`, `requires_upload`, and a `CreativeTypeHandler` with four hooks:

- `validate(content) -> dict` — normalise and store type-specific content.
- `project(content, media, is_owner, preview) -> response content` — shape for feed (preview) and detail; the only place that decides what other users may see.
- `moderation_texts(content)` — extra text to screen at publish.
- `redact(content)` — strip user-authored text on account deletion.

The generic `CreativeSessionService`, `PublicationService`, feed projection, moderation, account deletion, and `session_cleanup` job read the registry and never special-case a type.

### Contract

- `/api/v1/sessions` replaces the per-type session prefixes; `creative_type` is in the create body.
- `CreativeSession` returns generic `status` plus `stage` and `stage_timestamps`.
- `Submission` and `FeedItem` carry a discriminated `content` object (`SketchContent`, `StoryContent`, …) built from the registry instead of nullable flat fields.

### Preferences

Anything a user sets inside one app applies to that app only. Timer memory and the daily reminder move to `creative_type_preferences`; timezone, appearance, and profile stay account-wide (see `spec/product.md`).

## Consequences

- Adding a creative type is one backend module, one enum value, OpenAPI schema additions, and one iOS module conforming to `CreativeModule` (Stage 2). No new tables, services, routes, or jobs.
- Type-specific queries against `content` are JSONB lookups; anything that needs indexing (none today) would be promoted to a column.
- Existing sessions are backfilled with status/stage split (`ready_for_photo` → `active` + stage `ready_for_photo`, `writing` → `active` + stage `writing`); the downgrade path recreates the per-type tables and copies data back.
- iOS clients must adopt the new session and `content` shapes before this backend ships (single coordinated release; local caches are version-bumped).
