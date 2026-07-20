# Daily Sketch — Implementation Specification

**Version:** 1.1
**Status:** Canonical delivery plan
**Primary audience:** Cursor and human engineers
**Companion specifications:** `product.md`, `design.md`, `architecture.md`, `infrastructure.md`

## 1. Purpose of this document

This document defines how Daily Sketch should be implemented.

It converts the product, design, and architecture specifications into a phased engineering plan that can be executed incrementally in Cursor without losing product intent or introducing unnecessary complexity.

It is authoritative for:

- implementation order;
- phase boundaries;
- required deliverables;
- acceptance criteria;
- engineering workflow;
- testing expectations;
- contract-first sequencing;
- migration discipline;
- Cursor execution rules;
- release readiness.

The application should always remain runnable and deployable at the end of each phase.

---

## 2. Delivery principles

### 2.1 Build vertical slices

Each phase should deliver a complete user-visible capability where practical.

A vertical slice includes:

- OpenAPI contract;
- database migration;
- backend logic;
- iOS integration;
- loading/error states;
- tests;
- documentation.

Do not spend several phases building only infrastructure or backend layers that are not exercised by the client.

### 2.2 Contract before implementation

For every API-backed feature:

1. update `api/openapi/openapi.yaml`;
2. validate the contract;
3. review compatibility and examples;
4. generate or update Swift client types;
5. implement backend models and services;
6. implement route handlers;
7. add contract and integration tests;
8. implement iOS repositories/view models;
9. implement SwiftUI screens;
10. run end-to-end acceptance checks.

Backend code must not become the de facto contract.

### 2.3 Keep version one complete but focused

Do not add:

- Redis;
- queues;
- microservices;
- following;
- DMs;
- private accounts;
- recommendation ranking;
- user-generated prompts;
- Android;
- web client;
- cross-device Draft synchronisation.

### 2.4 Prefer explicit code

Avoid unnecessary abstractions, generic repository frameworks, service locators, or metaprogramming.

The code should make product rules obvious.

### 2.5 Preserve canonical language

Use:

- Daily Prompt;
- Prompt Date;
- Sketch Session;
- Timer Option;
- Draft;
- Submission;
- Like;
- Reflection;
- Streak.

Do not rename these concepts casually.

### 2.6 Every phase must be testable

A phase is not done when code compiles.

It is done when:

- automated tests pass;
- acceptance criteria are demonstrated;
- failure states are handled;
- documentation is updated;
- CI is green.

### 2.7 No hidden product decisions

When Cursor encounters ambiguity:

- inspect all five specification files;
- prefer the narrowest implementation consistent with the specs;
- document assumptions;
- create an ADR only for meaningful architectural decisions;
- do not silently invent new product behaviour.

### 2.8 Phase gates

Do not begin the next implementation phase while the current phase fails its acceptance criteria or leaves the repository unable to build, migrate, test, or run. A later phase may be explored in a separate branch, but it must not be presented as completed progress over a broken prerequisite.

### 2.9 Scope-safe changes

Do not refactor unrelated code while implementing a phase. Small prerequisite refactors are allowed only when they are necessary to deliver the requested slice, are covered by tests, and are reported explicitly.

### 2.10 Evidence over claims

Commands, tests, builds, migrations, and validation steps must be reported as actually run or not run. Cursor and human engineers must never state that a check passed when it was skipped, unavailable, or only inferred from code inspection.

---

## 3. Definition of done

A feature is complete only when all relevant items are true:

- OpenAPI contract updated;
- request and response examples included;
- database migration committed;
- backend implementation complete;
- authorisation rules covered;
- idempotency implemented where required;
- iOS API client updated;
- SwiftUI implementation complete;
- loading state present;
- empty state present where relevant;
- error and retry state present;
- accessibility labels present;
- Dynamic Type reviewed;
- dark mode reviewed;
- unit tests pass;
- integration tests pass;
- contract tests pass;
- manual device flow verified where relevant;
- README or developer documentation updated;
- no secrets or generated junk committed;
- CI passes.

---

## 4. Delivery phases

```text
Phase 0  — Repository, Tooling, and Local Environment
Phase 1  — Contract Foundation and Application Shell
Phase 2  — Descope Authentication and User Provisioning
Phase 3  — Profile Completion and Preferences
Phase 4  — Daily Prompt and Home Experience
Phase 5  — Sketch Sessions and Timer Flow
Phase 6  — Camera, Local Drafts, and Review Submission
Phase 7  — Direct Upload and Submission Publication
Phase 8  — Community Feed and Submission Detail
Phase 9  — Likes and Reflections
Phase 10 — Public Profiles, Streaks, and Native Sharing
Phase 11 — Safety, Blocking, Reporting, and Account Deletion
Phase 12 — Notifications, Recovery, Accessibility, and Polish
Phase 13 — Production Hardening and Release Readiness
```

Phases may be split into smaller pull requests, but should not be merged into one large unreviewable change.

---

# Phase 0 — Repository, Tooling, and Local Environment

## 5. Goals

Create a reliable project foundation before feature development begins.

## 5.1 Repository structure

Create:

```text
/
├── api/
│   ├── openapi/
│   │   └── openapi.yaml
│   ├── examples/
│   └── generated/
├── backend/
│   ├── app/
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

## 5.2 Backend setup

Configure:

- Python 3.14;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2.x;
- Alembic;
- async PostgreSQL driver;
- pytest;
- pytest-asyncio;
- httpx;
- Ruff;
- type checking with mypy or Pyright;
- pre-commit.

Recommended commands:

```text
make up
make seed
make backend-test
make backend-lint
make backend-typecheck
make db-migrate
make db-reset
```

Optional host tooling (CI):

```text
make backend-install
make backend-run
```

## 5.3 iOS setup

Create:

- SwiftUI app target;
- unit-test target;
- UI-test target;
- environment configuration;
- dependency container;
- typed navigation shell;
- initial design-system module;
- placeholder Home and Profile tabs.

## 5.4 Local infrastructure

Docker Compose provides:

- PostgreSQL;
- MinIO or another local S3-compatible service;
- backend service;
- optional migration one-shot service.

## 5.5 OpenAPI tooling

Add commands for:

```text
make api-validate
make api-generate-ios
make api-check-generated
```

CI must fail if generated code is stale.

## 5.6 Development quality gates

Configure:

- backend formatting;
- linting;
- type checking;
- tests;
- Swift build;
- Swift tests;
- secret scanning;
- Docker build.

## 5.7 Acceptance criteria

- repository builds from a clean clone;
- Docker Compose starts PostgreSQL and MinIO;
- backend health endpoint responds;
- Alembic can create a clean schema;
- iOS project builds in simulator;
- OpenAPI validation runs;
- CI pipeline runs on pull requests;
- README explains local setup;
- no real credentials committed.

---

# Phase 1 — Contract Foundation and Application Shell

## 6. Goals

Create the shared API conventions and visible iOS shell before feature-specific work.

## 6.1 OpenAPI foundation

Define:

- API metadata;
- `/api/v1` prefix;
- bearer authentication scheme;
- standard error schema;
- request ID header;
- cursor pagination schema;
- shared UUID and timestamp schemas;
- health endpoints.

Initial endpoints:

```text
GET /health/live
GET /health/ready
```

## 6.2 Backend foundation

Implement:

- application settings;
- database session dependency;
- request ID middleware;
- standard error handling;
- structured logging;
- health checks;
- explicit clock abstraction;
- storage adapter interface.

## 6.3 iOS shell

Implement:

- app environment selection;
- dependency injection root;
- two-tab layout: Home and Profile;
- settings route placeholder;
- semantic colour and typography tokens;
- reusable buttons and loading/error components;
- navigation routes.

## 6.4 Tests

- health endpoint contract tests;
- settings validation;
- request ID response header;
- iOS tab navigation tests;
- design-system snapshot or preview validation where useful.

## 6.5 Acceptance criteria

- backend and iOS app run together;
- Home and Profile tabs render;
- environment configuration works;
- contract validation is enforced;
- shared errors and pagination shapes are established.

---

# Phase 2 — Descope Authentication and User Provisioning

## 7. Goals

Support sign-up, sign-in, persistent authenticated sessions, and local application user provisioning.

## 7.1 Contract

Add:

```text
GET /api/v1/me
```

Define current-user response including:

- user ID;
- username;
- display name;
- profile completion state;
- account status;
- preferences summary.

## 7.2 Database

Create `users` migration.

Fields and constraints follow `architecture.md`.

## 7.3 Backend

Implement:

- Descope JWT verification;
- JWKS caching;
- issuer/audience validation;
- authenticated-user dependency;
- first-login provisioning;
- suspended/deleted user handling;
- `GET /me`.

## 7.4 iOS

Implement:

- Descope SDK integration;
- create-account flow;
- sign-in flow;
- secure session persistence;
- token attachment to API requests;
- token refresh/recovery;
- sign-out;
- guest versus authenticated app state.

Do not force authentication on first app launch.

## 7.5 Tests

Backend:

- valid JWT accepted;
- missing token rejected;
- invalid signature rejected;
- expired token rejected;
- local user provisioned once;
- repeated login resolves same user;
- suspended account rejected appropriately.

Client:

- guest shell available;
- sign-in changes app state;
- sign-out returns to guest state;
- token attached to authenticated request;
- expired session handled gracefully.

## 7.6 Acceptance criteria

- guest can open app;
- user can create account and sign in;
- authenticated session survives restart;
- backend provisions local user exactly once;
- `GET /me` works;
- sign-out clears authenticated state without deleting local Drafts.

---

# Phase 3 — Profile Completion and Preferences

## 8. Goals

Allow new users to complete a public profile and configure required preferences.

## 8.1 Contract

Add:

```text
PATCH /api/v1/me
GET   /api/v1/me/preferences
PATCH /api/v1/me/preferences
GET   /api/v1/users/{username}
```

## 8.2 Database

Add:

- profile fields and normalised username constraint;
- `user_preferences` table.

## 8.3 Backend

Implement:

- username validation;
- reserved usernames;
- case-insensitive uniqueness;
- display name update;
- bio update;
- profile-completion state;
- preference reads/updates;
- public profile projection.

## 8.4 iOS onboarding

Implement profile completion:

- username;
- display name;
- optional avatar placeholder;
- optional reminder setup;
- save and continue.

If onboarding follows guest publication intent, minimise steps and return to Review Submission quickly.

## 8.5 Settings foundation

Implement:

- profile summary;
- timer preference;
- reminder preference;
- appearance preference;
- sign out.

## 8.6 Tests

- username normalisation;
- reserved names rejected;
- duplicate names rejected;
- public profile excludes private data;
- preferences validate timer mode/seconds;
- incomplete profile cannot publish.

## 8.7 Acceptance criteria

- authenticated user can complete profile;
- username uniqueness works;
- preferences persist;
- public profile endpoint returns safe data;
- incomplete user is routed to completion before publishing.

---

# Phase 4 — Daily Prompt and Home Experience

## 9. Goals

Deliver the first recognisable product surface.

## 9.1 Contract

Add:

```text
GET /api/v1/prompts/today
GET /api/v1/prompts/{prompt_id}
GET /api/v1/feed/recent
```

Feed may initially return an empty list until Submissions exist.

## 9.2 Database

Create `daily_prompts`.

## 9.3 Prompt seed and publication

Create:

- curated word-list file;
- deterministic prompt-generation command;
- future prompt seed command;
- validation for three non-empty words;
- duplicate prevention within one prompt;
- ADR for global Prompt Date boundary.

## 9.4 Backend

Implement:

- current Prompt lookup;
- historical Prompt lookup by ID;
- missing-prompt error;
- development seed data;
- empty feed endpoint with correct contract.

## 9.5 iOS Home

Implement:

- corrected three-word PromptGroup;
- copy explaining all three words are used together;
- Start Sketch button;
- community-feed section;
- prompt loading state;
- feed loading state;
- empty feed state;
- feed error independent of prompt;
- cached prompt support where practical.

## 9.6 Tests

- one Prompt per date;
- all users see same current Prompt;
- Prompt words preserve order;
- Home renders all three words as one challenge;
- feed failure does not block Start Sketch;
- missing Prompt produces recoverable state.

## 9.7 Acceptance criteria

- guest and authenticated user can view today’s Prompt;
- Home matches `design.md` semantics;
- Start Sketch is the only initial creation action;
- community section appears below Prompt;
- Prompt remains usable during feed failure.

---

# Phase 5 — Sketch Sessions and Timer Flow

## 10. Goals

Implement timed and untimed creative sessions with recovery.

## 10.1 Contract

Add:

```text
POST /api/v1/sketch-sessions
GET  /api/v1/sketch-sessions/{session_id}
POST /api/v1/sketch-sessions/{session_id}/events
POST /api/v1/sketch-sessions/{session_id}/abandon
```

Define:

- timer mode enum;
- supported durations;
- session status enum;
- event enum;
- idempotency header.

## 10.2 Database

Create:

- `sketch_sessions`;
- `sketch_session_events`;
- `idempotency_keys` if not already present.

## 10.3 Backend

Implement:

- idempotent session creation;
- timer validation;
- ownership checks;
- event recording;
- pause/resume transitions;
- finish early;
- timer completed;
- abandon;
- session retrieval;
- server timestamps;
- expiry policy.

## 10.4 iOS Timer Selection

Implement fixed Stitch sheet:

- 1 minute;
- 3 minutes;
- 5 minutes;
- 10 minutes;
- No timer;
- Remember this choice, off by default;
- Start disabled until selection.

## 10.5 Remembered timer

Implement:

- local guest preference;
- server-backed authenticated preference;
- direct session start when remembered;
- Settings control to change or clear preference.

## 10.6 Active Sketch

Implement:

- countdown mode;
- No timer mode;
- Pause/Resume;
- Finish;
- Cancel;
- timer completion state;
- prompt accessibility;
- backgrounding;
- restoration after relaunch.

## 10.7 Guest sessions

Guest sessions are local until publication.

Persist:

- local session ID;
- Prompt;
- timer selection;
- start time;
- pause state;
- lifecycle state.

## 10.8 Tests

Backend:

- duplicate idempotency key returns same session;
- invalid duration rejected;
- transition rules enforced;
- ownership enforced;
- No timer valid.

Client:

- sheet appears by default;
- remembered option bypasses sheet;
- No timer can be remembered;
- countdown survives backgrounding;
- pause/resume correct;
- cancel confirmation works;
- guest session persists locally.

## 10.9 Acceptance criteria

- guest and authenticated user can start a session;
- all timer options work;
- No timer works;
- Remember this choice defaults off;
- active session recovers after interruption;
- backend tracks meaningful lifecycle events for authenticated sessions.

---

# Phase 6 — Camera, Local Drafts, and Review Submission

## 11. Goals

Complete the pre-publication flow before introducing remote media upload.

## 11.1 Local Draft model

Implement local persistence for:

- Draft ID;
- local/session ID;
- Prompt;
- timer metadata;
- image file path;
- caption;
- created/updated timestamps;
- pending authentication/publication state.

Use SwiftData, Core Data, or SQLite.

Do not use UserDefaults for image data.

## 11.2 Capture flow

Implement:

- camera permission handling;
- native camera capture;
- photo-library selection;
- permission-denied alternatives;
- image orientation handling;
- local image validation;
- retake/replace.

## 11.3 Review Submission

Implement:

- large image preview;
- Prompt metadata;
- timer metadata;
- optional caption;
- Replace/Retake;
- Submit to Community;
- Save to Drafts;
- keyboard handling;
- local state preservation.

## 11.4 Save Your Creativity

Implement guest authentication checkpoint:

- actual sketch thumbnail;
- Create Free Account;
- Sign In;
- Continue Later;
- preserved Draft through Descope flow;
- return to Review after authentication.

## 11.5 Draft recovery

Implement:

- Draft card on Home;
- reopen Review Submission;
- discard confirmation;
- cleanup after successful publication;
- retention cleanup policy.

## 11.6 Tests

- camera permission denied;
- library selection cancelled;
- image survives app restart;
- caption survives image replacement;
- guest auth preserves Draft;
- Continue Later returns Home;
- Draft reopens correctly;
- successful discard removes local file.

## 11.7 Acceptance criteria

- user can capture or choose a photo;
- Review Submission is mandatory;
- image can be replaced;
- caption is optional;
- Draft survives restart;
- guest can authenticate without losing work;
- no server upload required yet.

---

# Phase 7 — Direct Upload and Submission Publication

## 12. Goals

Publish a reviewed sketch safely to the backend and object storage.

## 12.1 Contract

Add:

```text
POST /api/v1/uploads
GET  /api/v1/uploads/{upload_id}
POST /api/v1/uploads/{upload_id}/complete
POST /api/v1/submissions
GET  /api/v1/submissions/{submission_id}
DELETE /api/v1/submissions/{submission_id}
```

## 12.2 Database

Create:

- `uploads`;
- `submissions`;
- required counters and indexes.

## 12.3 Storage adapter

Implement:

- signed upload creation;
- object verification;
- read URL generation;
- delete object;
- derivative key generation;
- local MinIO support.

## 12.4 Image processing

Implement bounded processing:

- decode validation;
- EXIF removal;
- orientation normalisation;
- display derivative;
- thumbnail;
- dimensions and size metadata.

Prefer synchronous or managed processing initially.

## 12.5 Backend publication transaction

Implement atomic flow:

1. validate user/profile;
2. validate session;
3. validate upload;
4. verify Prompt relationship;
5. create Submission;
6. consume Upload;
7. complete Sketch Session;
8. record event;
9. persist idempotent response.

## 12.6 iOS upload flow

Implement:

- optional image compression;
- upload-slot request;
- direct upload;
- progress display;
- completion call;
- Submission create;
- duplicate-safe retry;
- Draft preservation on failure;
- local Draft deletion after success.

## 12.7 Home completion state

After publish:

- Home refreshes;
- new Submission appears promptly;
- show You sketched today;
- show View My Sketch/View My Sketches;
- show Create Another Sketch.

## 12.8 Multiple Submissions

Ensure:

- separate Sketch Session per Submission;
- multiple Submissions for same Prompt allowed;
- streak date counted once.

## 12.9 Tests

- invalid MIME rejected;
- oversized image rejected;
- object missing rejected;
- Upload cannot be consumed twice;
- another user cannot consume Upload;
- duplicate Submission request returns same result;
- upload retry works;
- multiple Submissions for Prompt work;
- delete hides Submission.

## 12.10 Acceptance criteria

- authenticated user can publish;
- guest can authenticate then publish preserved work;
- upload progress visible;
- failure is retryable;
- duplicate publication prevented;
- successful Submission appears on Home;
- local Draft removed only after confirmed publication.

---

# Phase 8 — Community Feed and Submission Detail

## 13. Goals

Deliver the social browsing loop.

## 13.1 Contract

Finalise:

```text
GET /api/v1/feed/recent
GET /api/v1/submissions/{submission_id}
```

Feed projection includes:

- image URLs;
- user summary;
- Prompt summary;
- timer metadata;
- caption preview;
- Like count;
- Reflection count;
- viewer Like state;
- ownership flags.

## 13.2 Backend

Implement:

- reverse-chronological query;
- cursor pagination;
- published-content filtering;
- stable ordering;
- no N+1 queries;
- deleted/suspended filtering;
- placeholder block filtering ready for Phase 11.

## 13.3 iOS feed

Implement:

- SubmissionCard;
- image loading and caching;
- first-page loading;
- infinite scroll;
- pull to refresh;
- empty state;
- retry state;
- offline cached display where possible;
- navigation to detail/profile.

## 13.4 Submission Detail

Implement:

- artwork;
- owner row;
- three Prompt chips;
- date/timer;
- caption;
- Like/Reflection placeholders wired in next phase;
- Share placeholder;
- owner delete;
- report/block menu placeholders.

## 13.5 Tests

- feed ordering stable;
- cursor has no duplicate/skip under new inserts;
- deleted content excluded;
- new Submission appears;
- feed error does not hide Prompt;
- owner delete removes content from feed/detail/profile.

## 13.6 Acceptance criteria

- Home displays real Submissions;
- infinite scrolling works;
- artwork dominates layout;
- tapping owner opens Profile placeholder/public profile;
- tapping artwork opens Detail;
- deletion is reflected consistently.

---

# Phase 9 — Likes and Reflections

## 14. Goals

Complete version-one social interaction.

## 14.1 Contract

Add:

```text
PUT    /api/v1/submissions/{submission_id}/like
DELETE /api/v1/submissions/{submission_id}/like
GET    /api/v1/submissions/{submission_id}/reflections
POST   /api/v1/submissions/{submission_id}/reflections
DELETE /api/v1/reflections/{reflection_id}
```

## 14.2 Database

Create:

- `submission_likes`;
- `reflections`;
- `activity_events`;
- counters if not already added.

## 14.3 Backend Likes

Implement:

- idempotent Like;
- idempotent Unlike;
- counter updates;
- ownership/self-Like allowed unless product later changes;
- activity event for another user’s Submission;
- visibility/account validation.

## 14.4 Backend Reflections

Implement:

- body validation;
- create transaction;
- counter update;
- activity event;
- list pagination;
- author delete;
- removed/deleted filtering.

## 14.5 iOS Likes

Implement:

- optimistic heart toggle;
- sage active state;
- optimistic count;
- rollback on failure;
- guest auth checkpoint preserving intended action;
- no ranking UI.

## 14.6 iOS Reflections

Implement:

- Reflection thread;
- Add a reflection composer;
- character limit;
- Post state;
- guest authentication preserving text;
- delete own Reflection;
- retry preserving text.

## 14.7 Tests

- duplicate Like not duplicated;
- Unlike missing Like safe;
- counters correct;
- Reflection whitespace rejected;
- author delete only;
- deleted Reflection excluded/count decremented;
- activity event not created for self-action;
- guest flow returns correctly;
- optimistic rollback works.

## 14.8 Acceptance criteria

- authenticated users can Like/Unlike;
- authenticated users can post/delete Reflections;
- guests can read and are prompted to authenticate for writes;
- counts remain consistent;
- feed and detail update correctly;
- social interaction remains visually subordinate to artwork.

---

# Phase 10 — Public Profiles, Streaks, and Native Sharing

## 15. Goals

Turn each user’s history into a coherent sketch journal.

## 15.1 Contract

Finalise:

```text
GET /api/v1/users/{username}
GET /api/v1/users/{username}/submissions
```

Profile response includes:

- avatar;
- display name;
- username;
- bio;
- Submission count;
- current streak;
- ownership/viewer flags.

## 15.2 Backend

Implement:

- public profile lookup;
- paginated Submission history;
- streak query;
- deleted/suspended user behaviour;
- avatar upload flow if not completed earlier.

## 15.3 iOS Profile

Implement:

- own and other profiles;
- large journal-style gallery;
- profile pagination;
- empty state;
- Edit Profile;
- settings gear on own profile;
- navigation from feed/detail.

## 15.4 Native sharing

Implement iOS share sheet from Submission Detail.

Share payload:

- image or rendered share image;
- Prompt words;
- creator attribution;
- public/deep link when available;
- no signed storage URL leakage.

## 15.5 Tests

- public profile safe fields only;
- streak rules correct;
- multiple Submissions per day count once;
- delete final Submission changes streak;
- pagination stable;
- share payload contains no private URL/token.

## 15.6 Acceptance criteria

- users can browse another user’s history;
- own profile shows correct count and streak;
- profile gallery matches design intent;
- every gallery item opens Detail;
- native sharing works.

---

# Phase 11 — Safety, Blocking, Reporting, and Account Deletion

## 16. Goals

Add minimum viable safety and privacy operations for a public community.

## 16.1 Contract

Add:

```text
POST   /api/v1/reports
GET    /api/v1/me/blocked-users
PUT    /api/v1/users/{user_id}/block
DELETE /api/v1/users/{user_id}/block
DELETE /api/v1/me
```

## 16.2 Database

Create:

- `user_blocks`;
- `reports`;
- moderation audit model if required.

## 16.3 Backend blocking

Implement:

- block/unblock;
- feed filtering;
- profile behaviour;
- interaction restrictions;
- hidden Reflections;
- private block relationships.

## 16.4 Backend reporting

Implement:

- Submission report;
- Reflection report;
- profile report;
- duplicate/abuse protections;
- moderation status.

## 16.5 Moderation operations

Provide protected internal commands/endpoints for:

- list reports;
- hide/remove Submission;
- hide/remove Reflection;
- suspend user;
- restore content;
- record reason.

No public moderator UI required.

## 16.6 iOS safety UI

Implement:

- overflow menus;
- report reason sheet;
- block confirmation;
- blocked-users Settings screen;
- report success confirmation;
- content disappearance after block.

## 16.7 Account deletion

Implement:

- dedicated confirmation screen;
- backend pending-deletion state;
- public profile/content hiding;
- scheduled media cleanup;
- Descope identity coordination;
- local Draft cleanup;
- sign-out/completion.

## 16.8 Tests

- block filters content;
- blocked interaction rejected server-side;
- unblock restores visibility as defined;
- report created;
- unauthorised moderation rejected;
- account deletion idempotent;
- deleted account no longer public.

## 16.9 Acceptance criteria

- user can report content;
- user can block/unblock;
- moderation operator can remove abusive content;
- user can delete account;
- safety actions are enforced on backend, not only hidden in UI.

---

# Phase 12 — Notifications, Recovery, Accessibility, and Polish

## 17. Goals

Complete the user experience and ensure robust handling outside the happy path.

## 17.1 Local daily notifications

Implement:

- permission request at an appropriate moment;
- reminder enable/disable;
- reminder time;
- local scheduling;
- rescheduling after preference/timezone change;
- notification tap to Home;
- Settings shortcut if permission denied.

## 17.2 Recovery

Review and harden:

- active session restoration;
- local Draft restoration;
- pending upload recovery;
- pending Submission retry;
- expired auth session during publication;
- offline mode;
- signed upload expiry.

## 17.3 Accessibility

Complete:

- VoiceOver labels;
- prompt grouping;
- timer accessibility value;
- Like selected state;
- Dynamic Type;
- 44 pt touch targets;
- contrast review;
- Reduce Motion;
- keyboard navigation where relevant.

## 17.4 Dark mode

Review every screen and component using semantic tokens.

## 17.5 Error and empty states

Complete all states defined in `design.md`.

## 17.6 Product analytics

Implement privacy-conscious events for:

- prompt view;
- session funnel;
- Review Submission;
- auth checkpoint;
- Draft;
- upload/publication;
- feed/detail/profile;
- Like/Reflection;
- reminder setting.

## 17.7 Tests

- notification schedule/reschedule;
- notification deep link;
- offline Draft;
- auth expiry during upload;
- large Dynamic Type UI tests;
- VoiceOver smoke test;
- Reduce Motion behaviour;
- dark mode snapshots where useful.

## 17.8 Acceptance criteria

- reminders work on device;
- interruptions preserve work;
- all core flows accessible;
- dark mode complete;
- no dead-end error states;
- analytics do not contain sensitive payloads.

---

# Phase 13 — Production Hardening and Release Readiness

## 18. Goals

Prepare backend and iOS app for TestFlight and production release.

## 18.1 Backend hardening

Complete:

- timeouts;
- DB pool tuning;
- request-size limits;
- rate limits where needed;
- health/readiness checks;
- structured logging;
- metrics;
- tracing;
- cleanup jobs;
- backup validation;
- migration rollback planning.

## 18.2 Security review

Review:

- Descope configuration;
- JWT validation;
- storage policy;
- signed URL expiry;
- image validation;
- EXIF stripping;
- secrets;
- moderation access;
- account deletion;
- log redaction.

## 18.3 Performance review

Load and profile:

- current Prompt;
- feed first page;
- profile history;
- Like;
- Reflection creation;
- Submission creation;
- image rendering.

Add indexes only from measured query plans.

## 18.4 iOS release polish

Complete:

- permission strings;
- privacy manifest;
- App Store metadata;
- screenshots;
- support links;
- legal links;
- crash reporting;
- release environment configuration;
- physical-device test matrix.

## 18.5 Final end-to-end test

Verify:

1. guest opens app;
2. views Prompt and feed;
3. starts timed session;
4. backgrounds/reopens;
5. captures image;
6. reviews image;
7. reaches Save Your Creativity;
8. creates account;
9. completes profile;
10. publishes;
11. sees Home completion state;
12. creates second Submission;
13. Likes another Submission;
14. posts/deletes Reflection;
15. browses profile;
16. shares;
17. reports and blocks;
18. receives reminder;
19. deletes own Submission;
20. deletes account.

## 18.6 Acceptance criteria

- CI green;
- migrations tested;
- restore tested;
- security review complete;
- no known critical issue;
- physical-device core flow passes;
- staging deployment reproducible;
- TestFlight build ready;
- production rollback documented.

---

## 19. Backend coding conventions

## 19.1 Layering

Recommended request path:

```text
route
  -> request schema validation
  -> auth dependency
  -> application service
  -> repository/storage adapter
  -> database/object storage
```

Routes remain thin.

## 19.2 Domain services

Business rules belong in explicit services/functions such as:

- `PromptService`;
- `SketchSessionService`;
- `UploadService`;
- `SubmissionService`;
- `SocialService`;
- `ProfileService`;
- `ModerationService`;
- `AccountDeletionService`.

Avoid one large generic service.

## 19.3 Schemas

Separate:

- ORM models;
- API request models;
- API response models;
- internal service models.

Never return ORM entities directly.

## 19.4 Time

Use injectable clock abstraction for:

- current Prompt Date;
- session timing;
- upload expiry;
- streak calculation;
- account deletion;
- tests.

## 19.5 Transactions

Use transactions for:

- Submission creation;
- Like/unlike counter update;
- Reflection creation/deletion;
- block side effects if any;
- account status transitions.

## 19.6 Exceptions

Use stable domain exceptions mapped to API error codes.

Do not return arbitrary 500s for known cases.

---

## 20. iOS coding conventions

## 20.1 Feature organisation

Organise code by feature, with shared Core/DesignSystem modules.

## 20.2 Views

- views remain small;
- no networking in `body`;
- no business logic in button closures beyond invoking view model methods;
- use previews extensively.

## 20.3 View models

View models own:

- presentation state;
- async action coordination;
- error mapping;
- navigation intent.

Repositories own API/local persistence interaction.

## 20.4 Swift concurrency

Use structured concurrency.

Support:

- cancellation;
- main-actor UI state;
- non-blocking image work;
- safe task lifecycle.

## 20.5 Generated API client

Do not edit generated files manually.

Wrap generated client behind repositories.

## 20.6 Local files

Store Draft images in Application Support with file protection.

Clean up orphaned files.

## 20.7 Previews

Every major screen should preview:

- normal;
- loading;
- empty;
- error;
- dark mode;
- large Dynamic Type;
- guest/authenticated where relevant.

---

## 21. Database migration strategy

- every schema change has Alembic migration;
- migrations committed with feature;
- CI applies migrations to clean PostgreSQL;
- seed data separate from migrations;
- destructive changes require explicit plan;
- app instances do not auto-run migrations;
- rolling deployment compatibility considered;
- old iOS clients considered before removing fields.

---

## 22. Testing strategy

## 22.1 Backend unit tests

Cover:

- Prompt Date;
- username rules;
- timer validation;
- session transitions;
- Draft-to-session conversion logic;
- upload states;
- Submission eligibility;
- Like counter logic;
- Reflection rules;
- block filtering;
- streak calculation;
- account deletion.

## 22.2 Integration tests

Use real PostgreSQL and local object storage.

Cover:

- constraints;
- transactions;
- pagination;
- idempotency;
- upload verification;
- deletion visibility;
- counters;
- blocked queries.

## 22.3 Contract tests

Every endpoint:

- success response valid;
- known errors valid;
- auth rules match;
- examples valid;
- no undocumented fields relied upon.

## 22.4 iOS unit tests

Prioritise:

- auth state;
- Draft recovery;
- timer restoration;
- remembered preference;
- upload state machine;
- optimistic Like;
- Reflection preservation;
- feed pagination;
- profile/streak display;
- notification scheduling.

## 22.5 UI tests

Critical flows:

- guest creation to account publication;
- returning timed session;
- Draft reopen;
- Like and Reflection;
- Profile navigation;
- account deletion entry.

## 22.6 Manual device testing

Test:

- camera;
- photo library;
- backgrounding;
- screen lock;
- poor network;
- offline;
- notifications;
- Dynamic Type;
- VoiceOver;
- dark mode;
- large images;
- low storage where practical.

---

## 23. Seed and fixture data

Provide commands to create:

- future Prompts;
- several users;
- completed/incomplete profiles;
- public Submissions across dates;
- multiple Submissions per day;
- Likes;
- Reflections;
- blocked relationships;
- open reports;
- active/abandoned sessions;
- pending/failed uploads;
- users with no Submissions.

Use safe generated artwork fixtures.

Do not use real user data.

---

## 24. Cursor execution protocol

For every Cursor implementation task:

1. point Cursor at all files in `spec/`;
2. name exactly one phase or sub-phase;
3. require repository inspection before edits;
4. require conflict/missing prerequisite report;
5. require OpenAPI update first;
6. require migrations;
7. require backend tests;
8. require iOS tests;
9. require documentation update;
10. require commands run and outcomes;
11. require changed-file summary;
12. forbid out-of-scope features.

Recommended prompt:

```text
Implement Phase X from spec/implementation.md.

Treat the following as authoritative:
- spec/product.md
- spec/design.md
- spec/architecture.md
- spec/implementation.md
- spec/infrastructure.md
- api/openapi/openapi.yaml

Before editing:
1. inspect the repository;
2. identify relevant existing code;
3. list conflicts, missing prerequisites, or assumptions.

Then:
1. update the OpenAPI contract first;
2. add or update migrations;
3. implement backend behaviour;
4. update/generate the Swift client;
5. implement the SwiftUI experience;
6. add tests;
7. update README/developer docs;
8. run validation, lint, type-check, and tests.

Do not add Redis, queues, microservices, following, DMs, private profiles, or other out-of-scope features.

At the end, provide:
- changed files;
- commands run;
- results;
- assumptions;
- remaining risks.
```

Do not ask Cursor to implement multiple major phases in one prompt.

Cursor must not continue automatically into the next phase after finishing the requested phase. It should stop, report evidence, and identify the next smallest sensible task.

---

## 25. Release milestones

### Milestone A — Foundation

Phases 0–3.

User can:

- open app as guest;
- authenticate;
- complete profile;
- configure preferences.

### Milestone B — Creative Core

Phases 4–6.

User can:

- view Prompt;
- start timer;
- recover session;
- capture image;
- review and save Draft;
- reach guest auth checkpoint.

### Milestone C — Publish

Phase 7.

User can publish one or multiple Submissions.

### Milestone D — Community

Phases 8–10.

User can:

- browse feed;
- open detail;
- Like;
- add Reflections;
- browse profiles;
- share.

### Milestone E — Safe Beta

Phases 11–12.

Includes:

- reporting;
- blocking;
- account deletion;
- reminders;
- recovery;
- accessibility;
- polish.

### Milestone F — Production Ready

Phase 13.

Includes:

- hardening;
- security;
- performance;
- staging;
- TestFlight;
- release readiness.

---

## 26. Final version-one acceptance criteria

Version one is complete when:

- guest can browse Prompt/feed;
- guest can complete sketch and review flow;
- Save Your Creativity preserves work through authentication;
- Descope authentication works;
- profile completion works;
- all users see same three-word Prompt;
- timer options work;
- Remember this choice defaults off;
- No timer works;
- sessions recover after interruption;
- photo capture/library work;
- local Drafts work;
- direct signed upload works;
- duplicate publication prevented;
- multiple Submissions per Prompt Date work;
- Home completion state works;
- feed pagination works;
- detail works;
- Likes work;
- Reflections work;
- public profiles work;
- streaks work;
- native sharing works;
- blocking/reporting work;
- account deletion works;
- local reminders work;
- accessibility requirements pass;
- dark mode works;
- API conforms to OpenAPI;
- critical end-to-end tests pass;
- production deployment is repeatable.
