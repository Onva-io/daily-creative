# Daily Sketch — Architecture Specification

**Version:** 1.1
**Status:** Canonical technical baseline
**Primary client:** Native iOS using Swift and SwiftUI
**Backend:** Python 3.14 with FastAPI
**Database:** PostgreSQL
**Authentication:** Descope
**Media storage:** S3-compatible private object storage
**API style:** Contract-first OpenAPI

## 1. Purpose of this document

This document defines the technical architecture for Daily Sketch.

It is the authoritative source for:

- system boundaries;
- client/server responsibilities;
- data ownership;
- API design;
- domain models;
- authentication and authorisation;
- image upload and processing;
- feed, profile, Like, and Reflection behaviour;
- guest and Draft handling;
- error, idempotency, and retry semantics;
- security controls;
- technical testing expectations;
- future extension points.

Companion files have narrower responsibilities:

- `product.md` defines user behaviour, scope, and product rules.
- `design.md` defines visual presentation and interaction details.
- `implementation.md` defines build phases and acceptance gates.
- `infrastructure.md` defines environments, deployment, CI/CD, monitoring, secrets, and operations.

Where this document and `product.md` appear to conflict, `product.md` controls product intent and this document should be updated before implementation.

---

## 2. Architectural goals

The version-one architecture must:

- support a polished native iOS application;
- expose a stable, versioned HTTP API;
- use OpenAPI as the contract source of truth;
- use Descope for authentication and identity;
- use PostgreSQL as the durable system of record;
- store images outside PostgreSQL in private object storage;
- support direct client-to-storage uploads;
- support guest sketching before account creation;
- preserve guest work through authentication;
- support one shared three-word Daily Prompt per product date;
- support multiple Submissions per user per Prompt Date;
- track Sketch Sessions independently from published Submissions;
- support Likes and Reflections in version one;
- support public profiles and personal streak calculation;
- support a reverse-chronological feed without Redis;
- support reliable mobile retries and app interruption;
- remain deployable as one stateless backend service;
- avoid distributed systems until measured need justifies them;
- remain readable and maintainable for a small engineering team.

---

## 3. Guiding engineering principles

### 3.1 Contract first

The OpenAPI contract is defined before backend handlers and before client integration.

Do not implement endpoints and document them afterwards.

### 3.2 PostgreSQL is authoritative

All durable application state belongs in PostgreSQL, except media bytes.

The iOS client may cache data and preserve local Drafts, but client state must not become the only durable source for published content or authenticated preferences.

### 3.3 Stateless backend

Backend instances must not depend on in-memory session affinity, local disk, or a specific process.

Any instance should be able to serve any authenticated request.

### 3.4 Simple before distributed

Version one does not require:

- Redis;
- Kafka;
- SQS;
- Celery;
- Kubernetes;
- microservices;
- a dedicated recommendation service;
- a separate notification service.

Introduce these only after measured need.

### 3.5 Explicit domain boundaries

Use named domain concepts:

- Daily Prompt;
- Sketch Session;
- Upload;
- Draft;
- Submission;
- Like;
- Reflection;
- Profile;
- Streak;
- Block;
- Report;
- Activity Event.

Avoid generic “content” or “post” abstractions that obscure product behaviour.

### 3.6 Mobile requests are retryable

The API must assume:

- connections time out;
- users background the app;
- uploads complete but completion callbacks fail;
- write requests are retried;
- old iOS clients remain active during rollout.

Write operations must be idempotent where duplicate creation would be harmful.

### 3.7 Server time is authoritative

The backend records authoritative timestamps.

Client timestamps may be stored as advisory metadata but must not be used alone for security, ordering, or billing-like logic.

### 3.8 Build for observability

Key actions should be traceable by request ID, user ID where safe, and stable error code.

Do not rely on free-text logs to understand production behaviour.

---

## 4. High-level system architecture

```text
┌────────────────────────────────────┐
│ Native iOS Application             │
│ Swift + SwiftUI                    │
│                                    │
│ - guest experience                 │
│ - Descope SDK                      │
│ - timer UI                         │
│ - camera / photo picker            │
│ - local Draft persistence          │
│ - OpenAPI-generated API client     │
│ - local notifications              │
└─────────────────┬──────────────────┘
                  │
                  │ HTTPS / JSON
                  │ Bearer JWT when authenticated
                  ▼
┌────────────────────────────────────┐
│ FastAPI Backend                    │
│ Python 3.14                        │
│                                    │
│ - request validation               │
│ - JWT verification                 │
│ - authorisation                    │
│ - business rules                   │
│ - feed / profile queries           │
│ - signed upload orchestration      │
│ - moderation and safety            │
│ - activity-event recording         │
└──────────────┬───────────────┬─────┘
               │               │
               │ SQL           │ Signed URLs / metadata
               ▼               ▼
┌──────────────────────┐  ┌──────────────────────────┐
│ PostgreSQL           │  │ S3-Compatible Storage    │
│                      │  │                          │
│ - users              │  │ - original images        │
│ - profiles           │  │ - display derivatives    │
│ - prompts            │  │ - thumbnails             │
│ - sessions           │  │ - avatars                │
│ - uploads            │  │                          │
│ - submissions        │  └──────────────────────────┘
│ - likes              │
│ - reflections        │
│ - blocks             │
│ - reports            │
│ - events             │
└──────────────────────┘

External systems:

┌──────────────────────┐
│ Descope              │
│ Authentication       │
└──────────────────────┘

Optional later:

┌──────────────────────┐
│ APNs                 │
│ Remote notifications │
└──────────────────────┘
```

---

## 5. Technology choices

## 5.1 iOS client

The minimum supported operating system is **iOS 18.0**. The deployment target must be defined centrally in the Xcode project and build configuration so it cannot drift between targets.

Use:

- Swift;
- SwiftUI;
- Swift Concurrency (`async`/`await`);
- `NavigationStack`;
- `URLSession` or an OpenAPI-generated transport;
- Descope iOS SDK;
- `PhotosUI`;
- `AVFoundation` or native camera presentation;
- `UserNotifications`;
- Keychain for authentication material where required;
- lightweight local persistence for Drafts and recoverable sessions;
- native share sheet.

Avoid:

- React Native;
- Flutter;
- web views for core product screens;
- a large third-party state-management framework unless clearly justified;
- direct dependence of views on raw networking code.

## 5.2 Backend

Use:

- Python 3.14;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2.x;
- Alembic;
- async PostgreSQL driver;
- `httpx` where external HTTP calls are required;
- structured logging;
- OpenTelemetry-compatible tracing;
- Uvicorn.

Recommended supporting libraries may include:

- JWT/JWK verification library compatible with Descope;
- Pillow or libvips binding for image validation/derivatives;
- dependency injection through explicit FastAPI dependencies;
- rate-limiting middleware only when needed.

## 5.3 Database

Use PostgreSQL with:

- UUID primary keys;
- `timestamptz` for timestamps;
- explicit foreign keys;
- case-insensitive username constraint;
- partial indexes for active public content;
- JSONB only for flexible metadata, not core domain fields;
- Alembic-managed migrations.

## 5.4 Object storage

Use Amazon S3 or an S3-compatible provider.

Requirements:

- private buckets;
- short-lived signed upload URLs;
- opaque object keys;
- separate original and derived images;
- lifecycle cleanup for abandoned uploads;
- no permanent storage credentials in the iOS client.

## 5.5 Technology substitution policy

The selected platform stack is a product architecture decision, not a suggestion. Cursor and implementing engineers must not replace it with superficially similar services without an approved ADR and an explicit update to all affected specifications. In particular:

- do not replace native SwiftUI with React Native, Flutter, or a web wrapper;
- do not replace FastAPI with Firebase Functions, Supabase Edge Functions, or a different application backend;
- do not replace PostgreSQL with a client-direct document database;
- do not replace Descope with Firebase Authentication, Supabase Auth, or custom password storage;
- do not give the iOS client direct database access;
- do not use public object-storage buckets as a substitute for signed media access.

## 5.6 Authentication

Use Descope for:

- sign-up;
- sign-in;
- session management;
- token issuance;
- recovery flows;
- provider integrations if used.

The backend remains authoritative for application user status, username, profile, permissions, and moderation state.

---

## 6. Repository architecture

A monorepo is recommended.

```text
/
├── api/
│   ├── openapi/
│   │   └── openapi.yaml
│   ├── examples/
│   └── generated/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── core/
│   │   ├── db/
│   │   ├── domain/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── storage/
│   │   ├── observability/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── ios/
│   ├── DailySketch/
│   ├── DailySketchTests/
│   └── DailySketchUITests/
├── spec/
│   ├── product.md
│   ├── design.md
│   ├── architecture.md
│   ├── implementation.md
│   ├── infrastructure.md
│   └── decisions/
├── docker-compose.yml
├── Makefile
└── README.md
```

The OpenAPI contract must not be generated from FastAPI decorators as the primary workflow.

FastAPI may validate conformance, but `api/openapi/openapi.yaml` is the source of truth.

---

## 7. API contract-first workflow

## 7.1 Source of truth

`api/openapi/openapi.yaml` defines:

- paths;
- authentication requirements;
- request models;
- response models;
- enums;
- pagination;
- errors;
- examples;
- idempotency headers;
- nullable fields;
- public resource shapes.

## 7.2 Change workflow

For every API change:

1. update OpenAPI;
2. validate the contract;
3. review compatibility;
4. update examples;
5. generate or update Swift models/client;
6. implement backend;
7. add contract tests;
8. add integration tests;
9. connect UI;
10. document assumptions.

## 7.3 Versioning

Use:

```text
/api/v1
```

Breaking changes require:

- a new major API version; or
- an additive migration period with old fields/endpoints retained.

App Store rollout means older clients may remain active for days or weeks.

## 7.4 JSON conventions

Use:

- `snake_case` JSON properties;
- RFC 3339 UTC timestamps;
- UUID strings;
- explicit enums;
- explicit nullability;
- cursor pagination;
- stable machine-readable error codes.

## 7.5 Standard error response

```json
{
  "error": {
    "code": "submission_not_found",
    "message": "The requested sketch could not be found.",
    "details": {},
    "request_id": "f7d7c950-2892-4b6c-9300-ef6c5cbcb2d1"
  }
}
```

`message` must be user-safe.

Do not expose:

- SQL;
- stack traces;
- provider credentials;
- bucket names;
- raw exception text;
- JWT claims beyond safe identifiers.

## 7.6 Pagination shape

Recommended:

```json
{
  "items": [],
  "next_cursor": "opaque-value"
}
```

Cursor must be opaque to the client.

---

## 8. Authentication and identity

## 8.1 Authenticated request flow

1. User authenticates through Descope SDK.
2. Descope issues access/session token.
3. iOS sends:
   ```text
   Authorization: Bearer <token>
   ```
4. FastAPI verifies:
   - signature;
   - issuer;
   - audience;
   - expiry;
   - required claims.
5. Backend resolves local application user by immutable Descope subject.
6. Backend checks:
   - account status;
   - deletion state;
   - suspension state.
7. Request proceeds with an authenticated user context.

## 8.2 Local application user

Descope owns identity.

Daily Sketch owns:

- internal user UUID;
- username;
- display name;
- avatar;
- bio;
- account status;
- preferences;
- social relationships;
- moderation state;
- public history.

## 8.3 First-login provisioning

On first authenticated request:

- create local user if absent;
- mark profile as incomplete;
- store immutable Descope subject;
- assign a temporary internal handle if necessary;
- require username completion before publication.

Provisioning must be idempotent.

## 8.4 Guest identity

Guests do not receive durable server accounts.

The iOS client may create:

- a local guest installation ID;
- local Sketch Session IDs;
- local Draft IDs.

Guest identifiers must not be treated as authenticated identity.

When a guest signs in:

- preserve local Draft;
- create authenticated Sketch Session if needed;
- upload image;
- publish under authenticated user;
- avoid duplicate publication if the flow retries.

## 8.5 Authorisation

Backend owns all permission checks.

Examples:

- only owner can delete a Submission;
- only author can delete a Reflection;
- blocked users cannot interact;
- suspended users cannot publish;
- guests cannot Like or post Reflections;
- only upload owner can consume an upload;
- only privileged operators may moderate content.

Client-side hiding is not sufficient authorisation.

---

## 9. Domain model overview

```text
User
 ├── UserPreferences
 ├── DeviceRegistration (future/APNs)
 ├── SketchSessions
 ├── Uploads
 ├── Submissions
 ├── Likes
 ├── Reflections
 ├── Blocks
 └── Reports

DailyPrompt
 ├── three ordered words
 ├── prompt date
 ├── SketchSessions
 └── Submissions

SketchSession
 ├── timer selection
 ├── lifecycle timestamps
 ├── optional Submission
 └── session events

Upload
 ├── storage object
 ├── media metadata
 └── consumed by avatar or Submission

Submission
 ├── User
 ├── DailyPrompt
 ├── SketchSession
 ├── Upload
 ├── Likes
 ├── Reflections
 ├── Reports
 └── ActivityEvents
```

---

## 10. Database model

## 10.1 Users

```text
users
- id uuid pk
- descope_subject text unique not null
- username text
- username_normalized text unique
- display_name text
- bio text null
- avatar_upload_id uuid null
- status enum not null
- profile_completed_at timestamptz null
- created_at timestamptz not null
- updated_at timestamptz not null
- deleted_at timestamptz null
```

Suggested status:

```text
incomplete
active
suspended
pending_deletion
deleted
```

Rules:

- username unique case-insensitively;
- public queries include only appropriate active users;
- suspended user content treatment defined by moderation policy.

## 10.2 User preferences

```text
user_preferences
- user_id uuid pk fk users
- notifications_enabled boolean not null
- notification_time_local time null
- timezone text not null
- remember_timer_option boolean not null
- remembered_timer_mode enum null
- remembered_timer_seconds integer null
- appearance enum not null
- created_at timestamptz not null
- updated_at timestamptz not null
```

Timer mode:

```text
countdown
no_timer
```

Appearance:

```text
system
light
dark
```

## 10.3 Daily prompts

```text
daily_prompts
- id uuid pk
- prompt_date date unique not null
- word_1 text not null
- word_2 text not null
- word_3 text not null
- status enum not null
- created_at timestamptz not null
- published_at timestamptz null
- corrected_at timestamptz null
```

Prompt status:

```text
draft
published
withdrawn
```

Rules:

- exactly three non-empty words;
- preserve display order;
- one published prompt per Prompt Date;
- no per-user random prompt generation.

## 10.4 Sketch sessions

```text
sketch_sessions
- id uuid pk
- user_id uuid fk users not null
- prompt_id uuid fk daily_prompts not null
- timer_mode enum not null
- selected_timer_seconds integer null
- status enum not null
- started_at timestamptz not null
- paused_total_seconds integer not null default 0
- timer_completed_at timestamptz null
- finish_requested_at timestamptz null
- photo_step_reached_at timestamptz null
- upload_started_at timestamptz null
- upload_completed_at timestamptz null
- completed_at timestamptz null
- abandoned_at timestamptz null
- created_at timestamptz not null
- updated_at timestamptz not null
```

Suggested status:

```text
active
paused
ready_for_photo
uploading
completed
abandoned
expired
```

A session is private.

## 10.5 Sketch session events

```text
sketch_session_events
- id uuid pk
- sketch_session_id uuid fk
- event_type enum not null
- occurred_at timestamptz not null
- client_occurred_at timestamptz null
- metadata_json jsonb not null default '{}'
- created_at timestamptz not null
```

Events may include:

```text
started
paused
resumed
timer_completed
finished_early
photo_step_reached
upload_started
upload_completed
submission_created
abandoned
```

Use event rows for analytics and auditability.

Keep key timestamps denormalised on `sketch_sessions` for efficient reads.

## 10.6 Uploads

```text
uploads
- id uuid pk
- user_id uuid fk users not null
- purpose enum not null
- status enum not null
- storage_bucket text not null
- storage_key text unique not null
- original_filename text null
- content_type text not null
- byte_size bigint null
- width integer null
- height integer null
- checksum text null
- derivative_status enum null
- created_at timestamptz not null
- uploaded_at timestamptz null
- verified_at timestamptz null
- consumed_at timestamptz null
- expires_at timestamptz not null
- deleted_at timestamptz null
```

Purpose:

```text
submission
avatar
```

Status:

```text
pending
uploaded
verified
processing
ready
consumed
failed
expired
deleted
```

## 10.7 Submissions

```text
submissions
- id uuid pk
- user_id uuid fk users not null
- prompt_id uuid fk daily_prompts not null
- sketch_session_id uuid fk sketch_sessions unique not null
- upload_id uuid fk uploads unique not null
- caption text null
- visibility enum not null
- status enum not null
- published_at timestamptz not null
- created_at timestamptz not null
- updated_at timestamptz not null
- deleted_at timestamptz null
```

Visibility version one:

```text
public
```

Status:

```text
processing
published
hidden
removed
deleted
```

Multiple Submissions per user/prompt are allowed.

One Submission per Sketch Session.

## 10.8 Submission counters

Two valid approaches:

1. calculate counts from Like and Reflection tables;
2. maintain denormalised counters on Submission.

Recommended version one:

```text
submissions
- like_count integer not null default 0
- reflection_count integer not null default 0
```

Update atomically in transactions.

Counters are projections; source tables remain authoritative.

## 10.9 Likes

```text
submission_likes
- submission_id uuid fk submissions
- user_id uuid fk users
- created_at timestamptz not null
primary key (submission_id, user_id)
```

Unique composite key prevents duplicate Likes.

Unlike deletes the row.

## 10.10 Reflections

```text
reflections
- id uuid pk
- submission_id uuid fk submissions not null
- user_id uuid fk users not null
- body text not null
- status enum not null
- created_at timestamptz not null
- updated_at timestamptz not null
- deleted_at timestamptz null
```

Status:

```text
published
hidden
removed
deleted
```

No parent Reflection field in version one.

## 10.11 User blocks

```text
user_blocks
- blocker_user_id uuid fk users
- blocked_user_id uuid fk users
- created_at timestamptz not null
primary key (blocker_user_id, blocked_user_id)
```

Constraint:

- blocker and blocked cannot be same user.

## 10.12 Reports

```text
reports
- id uuid pk
- reporter_user_id uuid fk users not null
- target_type enum not null
- target_id uuid not null
- reason enum not null
- notes text null
- status enum not null
- created_at timestamptz not null
- reviewed_at timestamptz null
- reviewed_by_user_id uuid null
- resolution_notes text null
```

Target type:

```text
submission
reflection
profile
```

Status:

```text
open
reviewing
resolved
dismissed
```

Polymorphic target integrity must be enforced in application logic or separate report tables.

## 10.13 Activity events

```text
activity_events
- id uuid pk
- recipient_user_id uuid fk users not null
- actor_user_id uuid fk users null
- event_type enum not null
- submission_id uuid fk submissions null
- reflection_id uuid fk reflections null
- read_at timestamptz null
- created_at timestamptz not null
```

Event type:

```text
submission_liked
reflection_added
```

Version one records these for future Activity UI or push notifications.

A full Activity inbox endpoint is optional for version one.

## 10.14 Idempotency keys

```text
idempotency_keys
- id uuid pk
- user_id uuid fk users not null
- endpoint text not null
- key text not null
- request_hash text not null
- response_status integer null
- response_body jsonb null
- created_at timestamptz not null
- expires_at timestamptz not null
unique (user_id, endpoint, key)
```

Use for duplicate-sensitive writes.

---

## 11. Local Draft architecture

## 11.1 Scope

Version one Drafts are local to the iOS device.

A Draft contains:

- local Draft UUID;
- local guest/session UUID;
- Prompt ID and words;
- Prompt Date;
- timer mode;
- selected timer seconds;
- session start time;
- local image file reference;
- optional caption;
- review state;
- creation/update times;
- pending-authentication state;
- pending-publication state.

## 11.2 Storage

Use a lightweight local database or structured persistence.

Suitable options:

- SwiftData;
- SQLite wrapper;
- Core Data.

Do not store image bytes inside UserDefaults.

Store image files in the app’s private Application Support directory with file protection enabled.

## 11.3 Draft lifecycle

Create a Draft when:

- user chooses Save to Drafts;
- guest chooses Continue Later;
- upload fails and the user leaves;
- app is terminated after photo capture and before publication.

Delete local Draft after:

- successful publication;
- explicit discard;
- retention expiry;
- account deletion where appropriate.

## 11.4 Guest-to-authenticated conversion

After authentication:

1. preserve local Draft ID;
2. create authenticated Sketch Session;
3. create upload slot;
4. upload image;
5. create Submission idempotently;
6. delete local Draft after confirmed publication.

The UI remains on Review Submission throughout.

---

## 12. Prompt date and streak model

## 12.1 Global prompt date

The product requires one shared prompt at a time.

The global Prompt Date boundary is canonical and fixed for version one:

- the active prompt changes at **00:00 UTC**;
- `prompt_date` is derived from the UTC calendar date;
- all clients receive the same active Prompt regardless of the user's local timezone.

Changing this rule requires an ADR, a product decision, a data-migration review, and updates to all affected specifications. The UTC boundary must be used consistently by:

- prompt publication;
- today endpoint;
- streak calculation;
- feed metadata;
- notifications copy.

## 12.2 Streak calculation

A user participates on a Prompt Date when at least one active published Submission exists for that prompt.

Current streak:

- counts consecutive Prompt Dates;
- ending today if user has submitted today;
- otherwise ending yesterday if yesterday was completed;
- otherwise zero;
- multiple Submissions on one date count once;
- deleted/removed final Submission can reduce the streak.

Options:

- calculate on profile query;
- maintain a materialised projection.

Recommended version one:

- calculate with an indexed query;
- add a cached projection only if measured performance requires it.

---

## 13. API resource design

The exact schemas belong in OpenAPI.

## 13.1 Health

```text
GET /health/live
GET /health/ready
```

## 13.2 Current user

```text
GET    /api/v1/me
PATCH  /api/v1/me
DELETE /api/v1/me
```

`GET /me` returns:

- internal public-safe user data;
- profile-completion state;
- preferences summary;
- moderation/account status;
- current streak;
- submission count.

## 13.3 Preferences

```text
GET   /api/v1/me/preferences
PATCH /api/v1/me/preferences
```

Fields:

- reminder enabled;
- reminder time;
- timezone;
- remember timer;
- timer mode;
- timer seconds;
- appearance.

## 13.4 Public users

```text
GET /api/v1/users/{username}
GET /api/v1/users/{username}/submissions
```

Public profile excludes:

- email;
- Descope subject;
- block relationships;
- preferences;
- moderation internals;
- Drafts;
- private session analytics.

## 13.5 Daily prompts

```text
GET /api/v1/prompts/today
GET /api/v1/prompts/{prompt_id}
GET /api/v1/prompts/by-date/{date}
GET /api/v1/prompts/{prompt_id}/submissions
```

The by-date and prompt-submissions endpoints may be implemented after the core feed if not needed immediately by version-one screens, but should be in the planned contract.

## 13.6 Sketch sessions

```text
POST  /api/v1/sketch-sessions
GET   /api/v1/sketch-sessions/{session_id}
PATCH /api/v1/sketch-sessions/{session_id}
POST  /api/v1/sketch-sessions/{session_id}/events
POST  /api/v1/sketch-sessions/{session_id}/abandon
```

Session creation request:

- prompt ID;
- timer mode;
- timer seconds where applicable;
- client timezone;
- optional client Draft/session ID;
- idempotency key.

Event endpoint supports lifecycle events.

## 13.7 Uploads

```text
POST /api/v1/uploads
GET  /api/v1/uploads/{upload_id}
POST /api/v1/uploads/{upload_id}/complete
```

Create response:

- upload ID;
- signed URL;
- method;
- required headers;
- expiry;
- allowed size;
- allowed content type.

Complete verifies object and begins derivative processing.

## 13.8 Submissions

```text
POST   /api/v1/submissions
GET    /api/v1/submissions/{submission_id}
DELETE /api/v1/submissions/{submission_id}
```

Create request:

- Sketch Session ID;
- verified Upload ID;
- optional caption.

Backend derives:

- owner;
- Prompt;
- timer metadata.

## 13.9 Feed

```text
GET /api/v1/feed/recent
```

Parameters:

- `cursor`;
- `limit`.

Response item should contain enough data to render without N+1 calls:

- Submission summary;
- display image URLs;
- user summary;
- Prompt summary;
- timer metadata;
- caption preview;
- Like count;
- Reflection count;
- `viewer_has_liked`;
- ownership flags.

## 13.10 Likes

```text
PUT    /api/v1/submissions/{submission_id}/like
DELETE /api/v1/submissions/{submission_id}/like
```

`PUT` is naturally idempotent.

Alternative POST/DELETE is acceptable if contract defines idempotency.

Responses include:

- `liked`;
- updated count.

## 13.11 Reflections

```text
GET    /api/v1/submissions/{submission_id}/reflections
POST   /api/v1/submissions/{submission_id}/reflections
DELETE /api/v1/reflections/{reflection_id}
```

Create request:

- body;
- idempotency key.

List uses cursor pagination if needed.

## 13.12 Reports

```text
POST /api/v1/reports
```

Request:

- target type;
- target ID;
- reason;
- optional notes.

## 13.13 Blocks

```text
GET    /api/v1/me/blocked-users
PUT    /api/v1/users/{user_id}/block
DELETE /api/v1/users/{user_id}/block
```

Block/unblock is idempotent.

---

## 14. Feed architecture

## 14.1 Source

Read directly from PostgreSQL.

No Redis cache in version one.

## 14.2 Ordering

```text
published_at DESC, id DESC
```

Use stable cursor pagination.

## 14.3 Filtering

Exclude:

- deleted Submissions;
- removed Submissions;
- hidden Submissions not visible to viewer;
- content from suspended/deleted users where policy requires;
- content from users blocked by viewer;
- content from users who blocked viewer where reciprocal filtering applies.

## 14.4 Query projection

Use one efficient query or a small predictable set.

Avoid N+1 queries for:

- user;
- Prompt;
- counts;
- viewer Like state.

## 14.5 Future ranking

Future feed modes may include:

- today;
- following;
- popular;
- recommended.

Do not hard-code recency assumptions into iOS data models.

The API may later accept:

```text
mode=recent|today|following|popular
```

Version one uses `recent`.

---

## 15. Likes architecture

Like transaction:

1. validate authenticated user;
2. validate visible Submission;
3. validate block restrictions;
4. insert row with conflict-safe semantics;
5. increment counter only if row inserted;
6. create activity event unless actor owns Submission;
7. return updated state.

Unlike:

1. delete matching Like;
2. decrement counter only if row deleted;
3. prevent counter below zero;
4. optionally remove unread activity event if product chooses;
5. return updated state.

Database uniqueness prevents duplicates.

---

## 16. Reflection architecture

Create Reflection transaction:

1. authenticate;
2. validate profile complete and active;
3. validate visible Submission;
4. validate block restrictions;
5. validate body length/content;
6. create Reflection;
7. increment counter;
8. create activity event unless author owns Submission;
9. return public Reflection projection.

Delete Reflection:

1. authenticate;
2. verify author or privileged moderator;
3. mark deleted or hard-delete according to audit needs;
4. decrement counter;
5. hide from public queries.

No nested replies.

---

## 17. Blocking semantics

A block affects query and write behaviour.

For viewer A blocking user B:

- B’s Submissions hidden from A’s feed;
- B’s profile unavailable or shown as blocked;
- B’s Reflections hidden from A;
- A cannot Like or reflect on B’s content;
- B cannot interact with A where reciprocal restriction is implemented;
- existing Likes may remain in aggregate counts but viewer-specific state is hidden;
- existing Reflections may remain for moderation/audit but are not shown to blocker.

Block relationships are private.

---

## 18. Image upload architecture

## 18.1 Direct upload flow

```text
1. iOS requests upload slot.
2. Backend creates pending Upload row.
3. Backend returns signed PUT or multipart details.
4. iOS uploads directly to object storage.
5. iOS calls upload-complete.
6. Backend verifies object metadata.
7. Backend validates image.
8. Backend creates derivatives.
9. Upload becomes ready.
10. iOS creates Submission.
11. Backend consumes Upload and completes Sketch Session.
```

## 18.2 Validation

Validate:

- content type;
- maximum size;
- actual image decoding;
- dimensions;
- orientation;
- checksum where available;
- object existence;
- owner;
- expiry;
- single consumption.

Do not trust filename or extension.

## 18.3 Derivatives

Recommended:

- original retained privately;
- display derivative;
- feed/profile thumbnail;
- avatar derivative for avatar uploads.

Processing may be synchronous for an early beta if bounded.

If asynchronous:

- Submission may begin in `processing`;
- client displays processing state;
- background job must be durable.

Version one should avoid adding a durable queue unless necessary.

## 18.4 Metadata stripping

Remove unnecessary EXIF metadata, including precise location.

## 18.5 Read URLs

API returns:

- short-lived signed URLs; or
- stable CDN URLs backed by private storage.

Client must not know bucket names or storage keys.

---

## 19. Submission creation transaction

Submission creation must be atomic.

Within one transaction:

1. validate idempotency key;
2. validate authenticated user active;
3. validate Sketch Session ownership;
4. validate Upload ownership;
5. validate Upload ready and unconsumed;
6. validate session Prompt;
7. validate one Submission per session;
8. create Submission;
9. mark Upload consumed;
10. mark Sketch Session completed;
11. record session event;
12. initialise counters;
13. store idempotent response.

If the response is lost, retry returns same Submission.

---

## 20. Notification architecture

## 20.1 Daily reminder

Use local iOS notifications in version one.

The backend stores preference values for account portability and analytics.

Client schedules local notification based on:

- enabled flag;
- reminder local time;
- timezone.

## 20.2 Social activity

Backend records activity events for:

- Like received;
- Reflection received.

Version one does not require APNs delivery or an Activity inbox.

## 20.3 Future APNs

Future architecture may add:

- device registrations;
- APNs token storage;
- notification preferences by event type;
- durable worker;
- delivery status;
- deep-link payload.

Do not add this infrastructure before needed.

---

## 21. iOS application architecture

## 21.1 Feature-oriented structure

```text
DailySketch/
├── App/
├── Core/
│   ├── API/
│   ├── Auth/
│   ├── DesignSystem/
│   ├── Navigation/
│   ├── Persistence/
│   ├── Media/
│   ├── Notifications/
│   └── Utilities/
├── Features/
│   ├── Authentication/
│   ├── Home/
│   ├── TimerSelection/
│   ├── SketchSession/
│   ├── Capture/
│   ├── ReviewSubmission/
│   ├── Drafts/
│   ├── SubmissionDetail/
│   ├── Reflections/
│   ├── Profile/
│   ├── Settings/
│   ├── Reporting/
│   └── Blocking/
└── Resources/
```

## 21.2 View and domain boundaries

SwiftUI views must not perform network requests, object-storage operations, persistence queries, authentication orchestration, or domain-rule evaluation directly. Views render state and send user intents to a view model or equivalent presentation object.

Generated OpenAPI client files must never be edited manually. Any required API change begins in `api/openapi/openapi.yaml`, followed by regeneration. Handwritten application code may wrap generated types and operations but must not fork their definitions.

## 21.3 State ownership

Use:

- app-level authentication state;
- app-level environment/dependency container;
- per-feature observable view models;
- local Draft repository;
- active Sketch Session repository;
- navigation coordinator or typed routes.

Avoid one global object containing all feature state.

## 21.4 API client

Prefer OpenAPI-generated request/response types.

Wrap generated client with domain repositories where helpful.

Example:

```text
PromptRepository
SessionRepository
SubmissionRepository
SocialRepository
ProfileRepository
```

Do not duplicate every API model manually.

## 21.5 Image cache

Use native URL cache or a small established image-loading library.

Requirements:

- memory-conscious;
- disk caching;
- cancellation;
- placeholders;
- signed-URL expiry handling.

## 21.6 Active session recovery

Persist:

- local/session ID;
- server session ID;
- Prompt;
- timer mode;
- selected seconds;
- server start time;
- pause state;
- latest lifecycle state.

On relaunch:

1. restore local state;
2. fetch server session when authenticated/online;
3. reconcile using server timestamps;
4. route to active, photo, or review state.

## 21.7 Offline behaviour

Supported offline:

- cached Home;
- Start Sketch;
- timer;
- capture;
- Review Submission;
- Draft save.

Requires online:

- authentication;
- publication;
- Likes;
- Reflections;
- reports;
- profile refresh.

---

## 22. Timer semantics

## 22.1 Countdown

The client presents countdown using:

- server start time;
- selected duration;
- pause events;
- local monotonic clock for smooth rendering.

Server does not tick every second.

## 22.2 Pause

For authenticated sessions:

- client posts pause/resume events;
- server stores authoritative timestamps;
- client remains responsive if temporarily offline and syncs later.

## 22.3 No timer

No timer stores:

- mode `no_timer`;
- no selected seconds;
- start and later lifecycle times.

## 22.4 Elapsed session interval

Derived:

```text
submission_created_at - started_at
```

or other lifecycle intervals.

Never label as exact active drawing time.

---

## 23. Security architecture

## 23.1 API

- HTTPS only;
- JWT validation;
- request size limits;
- schema validation;
- ownership checks;
- parameterised SQL;
- stable errors;
- rate limiting for abuse-prone endpoints;
- idempotency for writes.

## 23.2 Storage

- private bucket;
- least-privilege credentials;
- short-lived signed URLs;
- fixed object key;
- content restrictions;
- orphan cleanup;
- no credentials in app.

## 23.3 Secrets

Secrets supplied via environment-specific secret management.

Never commit:

- Descope management credentials;
- database credentials;
- storage credentials;
- signing secrets;
- APNs keys.

## 23.4 Abuse controls

Rate-limit or protect:

- Reflection creation;
- report creation;
- upload-slot creation;
- username changes;
- authentication-sensitive endpoints.

## 23.5 Privacy

- strip EXIF;
- no precise location;
- do not log tokens;
- minimise user data in logs;
- protect Draft files with iOS file protection.

---

## 24. Error and retry semantics

## 24.1 Read requests

Reads may be retried safely.

Use:

- sensible timeouts;
- exponential backoff;
- cancellation;
- cached fallback where useful.

## 24.2 Write requests

Use idempotency for:

- Sketch Session creation;
- upload-slot creation where duplication matters;
- Submission creation;
- Reflection creation if retry could duplicate.

Use idempotent verbs for:

- Like (`PUT`);
- Unlike (`DELETE`);
- Block (`PUT`);
- Unblock (`DELETE`).

## 24.3 Upload retries

If direct upload succeeds but completion fails:

- reuse Upload ID;
- completion verifies object;
- do not upload again unnecessarily.

If signed URL expires:

- request replacement for same Upload when safe;
- or create new Upload and invalidate old.

## 24.4 Client preservation

On recoverable failure:

- preserve caption;
- preserve Reflection text;
- preserve image;
- preserve Draft;
- preserve intended post-auth action.

---

## 25. Database indexing

Initial indexes:

```text
users(username_normalized)
users(descope_subject)

daily_prompts(prompt_date)

submissions(published_at desc, id desc)
submissions(user_id, published_at desc, id desc)
submissions(prompt_id, published_at desc, id desc)

sketch_sessions(user_id, created_at desc)
sketch_sessions(prompt_id, created_at desc)

uploads(user_id, created_at desc)
uploads(status, expires_at)

submission_likes(user_id, created_at desc)

reflections(submission_id, created_at asc, id asc)
reflections(user_id, created_at desc)

user_blocks(blocker_user_id)
user_blocks(blocked_user_id)

reports(status, created_at)
activity_events(recipient_user_id, created_at desc)
```

Use partial indexes for:

- published non-deleted Submissions;
- active Reflections;
- pending uploads.

Validate with query plans.

---

## 26. Moderation architecture

Version one requires basic operational capability.

Support privileged service functions or protected endpoints to:

- list open reports;
- inspect target;
- hide/remove Submission;
- hide/remove Reflection;
- suspend user;
- restore content;
- record resolution.

Administrative actions require audit records.

Do not expose moderator APIs to the iOS public client.

A full moderation UI may be deferred.

---

## 27. Account deletion architecture

Recommended flow:

1. user requests deletion;
2. account status becomes `pending_deletion`;
3. access disabled;
4. public profile hidden;
5. Submissions hidden;
6. asynchronous or scheduled deletion removes media;
7. Likes/Reflections removed or anonymised according to policy;
8. Descope identity deleted/disabled;
9. required audit data retained minimally;
10. account marked deleted.

Deletion must be idempotent.

If no durable worker exists, use a scheduled platform job.

---

## 28. Observability

## 28.1 Structured logging

Include:

- request ID;
- route;
- method;
- status;
- latency;
- application version;
- environment;
- authenticated user UUID where safe;
- error code.

Do not log:

- JWT;
- signed URLs;
- image bytes;
- email;
- Draft content;
- raw captions/Reflections unless explicitly needed for moderation and securely handled.

## 28.2 Metrics

Track:

- request count/latency;
- errors;
- DB pool;
- prompt endpoint latency;
- feed latency;
- upload success/failure;
- Submission creation;
- Like/Reflection writes;
- session completion/abandonment;
- report creation;
- blocked interactions.

## 28.3 Tracing

Trace:

- auth resolution;
- upload verification;
- Submission transaction;
- feed query;
- Reflection creation;
- account deletion.

---

## 29. Testing architecture

## 29.1 Contract tests

Validate every endpoint against OpenAPI:

- success;
- validation errors;
- authentication errors;
- permission errors;
- pagination;
- nullability;
- enums;
- examples.

## 29.2 Backend unit tests

Test:

- username rules;
- prompt date;
- timer validation;
- session transitions;
- streak calculation;
- Like counter logic;
- Reflection rules;
- block filtering;
- report validation;
- idempotency;
- account status rules.

## 29.3 Backend integration tests

Use real PostgreSQL.

Cover:

- constraints;
- transactions;
- indexes/query shape;
- feed pagination;
- Submission creation;
- duplicate retries;
- delete visibility;
- block filtering.

Do not rely solely on SQLite.

## 29.4 Storage tests

Use MinIO or test S3-compatible storage.

Test:

- signed upload;
- expiry;
- verification;
- invalid media;
- derivative creation;
- orphan cleanup.

## 29.5 iOS tests

Test:

- auth state;
- guest Draft;
- guest-to-account conversion;
- remembered timer;
- timer recovery;
- upload retry;
- optimistic Like rollback;
- Reflection text preservation;
- feed pagination;
- profile state;
- notification scheduling.

## 29.6 End-to-end test

Automated or repeatable:

1. authenticate;
2. fetch prompt;
3. create session;
4. upload image;
5. create Submission;
6. see in feed;
7. Like;
8. add Reflection;
9. see on profile;
10. delete Reflection;
11. delete Submission.

---

## 30. Performance expectations

Initial targets:

- prompt endpoint p95 under 300 ms;
- recent feed p95 under 500 ms excluding image transfer;
- profile submissions p95 under 500 ms;
- Like/unlike p95 under 300 ms;
- Reflection create p95 under 500 ms;
- Submission create p95 under 700 ms excluding upload;
- no duplicate write effects from retries.

PostgreSQL should handle early-stage scale without Redis.

Optimise only after measurement.

---

## 31. Architectural decisions to record

Create ADRs in `spec/decisions/` for:

- contract-first OpenAPI;
- native SwiftUI;
- Descope authentication;
- PostgreSQL without Redis;
- S3 direct uploads;
- separate Sketch Session;
- local Draft model;
- global Prompt Date boundary;
- local notifications for version one;
- Likes and Reflections;
- block semantics;
- activity events without APNs delivery;
- image processing approach;
- account deletion;
- monorepo structure.

---

## 32. Future evolution

Possible later additions:

- Redis for measured hot reads;
- CDN-backed media delivery;
- durable background jobs;
- APNs push;
- Activity inbox;
- following graph;
- recommendation/ranking service;
- analytics warehouse;
- moderator web console;
- web and Android clients;
- cross-device Drafts;
- search;
- prompt-history browsing.

Future additions must preserve:

- API compatibility;
- PostgreSQL authority;
- clear domain language;
- no unnecessary coupling between client and storage internals.

---

## 33. Canonical architecture decisions

- SwiftUI native iOS client.
- Minimum supported operating system is iOS 18.0.
- Python 3.14 FastAPI backend.
- PostgreSQL as durable application store.
- No Redis in version one.
- Descope for authentication.
- Platform substitutions require an approved ADR and specification update.
- OpenAPI file is the API source of truth.
- Generated OpenAPI client code is never edited manually.
- Direct signed uploads to private S3-compatible storage.
- Sketch Session separate from Submission.
- Guest work preserved locally before authentication.
- Drafts local-only in version one.
- The global Prompt Date rolls over at 00:00 UTC.
- One global Daily Prompt per Prompt Date.
- Multiple Submissions per user per Prompt Date.
- Likes and Reflections included in version one.
- Feed reverse chronological and database-backed.
- Blocks filter reads and writes.
- Activity events recorded; push delivery deferred.
- Local daily reminders in version one.
- One stateless backend service.
- No queues or microservices until measured need.

## Multi-Creative-Type Architecture

The platform supports multiple creative types (sketch, story, and future types) through:

- **Independent session tables**: Each creative type has its own `*_sessions` and `*_session_events` tables with type-specific status enums and columns. No shared/polymorphic sessions table.
- **Shared submissions**: The `submissions` table has a `creative_type` discriminator. Each submission links to exactly one session type via nullable FKs (`sketch_session_id`, `story_session_id`) enforced by a check constraint.
- **Shared social layer**: Likes, reflections, blocks, and reports remain keyed on `submission_id` regardless of creative type.
- **Type-scoped queries**: Feed, profile, and streak endpoints accept an optional `creative_type` filter parameter.
- **Per-type iOS targets**: DailySketch and DailyStory are separate app targets sharing code from DailyCore (auth, profile, design system, social). Each target has its own session flow, branding, and build configuration.
- **ProductConfig**: Info.plist-driven branding (`BRAND_NAME`, `CREATIVE_TYPE_ID`) allows each app target to customize UI without code changes.

To add a new creative type, see the "Adding a Future Creative Type" section in the [plan](../plans/daily_creative_platform.plan.md).
