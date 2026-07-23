# Daily Creative — Infrastructure Specification

**Version:** 1.1
**Status:** Canonical infrastructure and operations baseline
**Primary audience:** Engineers operating local, staging, and production environments
**Companion specifications:** `product.md`, `design.md`, `architecture.md`, `implementation.md`

## 1. Purpose of this document

This document defines how Daily Creative should be run, deployed, secured, monitored, backed up, and maintained.

It is authoritative for:

- local development infrastructure;
- remote environments;
- containerisation;
- PostgreSQL provisioning;
- object storage;
- secrets management;
- CI/CD;
- infrastructure as code;
- logging, metrics, tracing, and alerting;
- scheduled jobs and cleanup;
- backup and recovery;
- release and rollback;
- operational security;
- cost and capacity controls.

This document does not define product behaviour, visual design, domain modelling, or implementation order except where infrastructure requirements directly affect them.

---

## 2. Infrastructure principles

### 2.1 Managed services first

Prefer managed services for:

- PostgreSQL;
- object storage;
- TLS termination;
- DNS;
- container hosting;
- secret storage;
- logging and metrics;
- backups.

The project should minimise operational burden for a small engineering team.

### 2.2 Stateless application service

The FastAPI backend must be stateless.

Application containers must not depend on:

- local disk for durable application data;
- in-memory sessions;
- sticky routing;
- a specific process;
- manual changes made after deployment;
- locally stored images.

Any running instance should be able to serve any request.

### 2.3 Environment isolation

Local, development, staging, and production must use separate:

- databases;
- object-storage buckets or accounts;
- secrets;
- Descope configurations;
- API hostnames;
- logs and metrics;
- deployment identities.

Production data must never be copied into lower environments without explicit anonymisation.

### 2.4 Reproducibility

Infrastructure and deployment configuration must be version controlled.

A new environment should be reproducible from:

- infrastructure code;
- application repository;
- environment-specific secrets;
- documented bootstrap steps.

### 2.5 Least privilege

Every service identity, CI job, and engineer account receives only the permissions required for its role.

### 2.6 Proportional complexity

Version one does not require:

- Kubernetes;
- Redis;
- Celery;
- Kafka;
- SQS;
- a service mesh;
- multi-region active-active deployment;
- multiple backend services.

Add operational complexity only after measured need.

### 2.7 Safe change

Every production change should be:

- reviewable;
- testable;
- traceable to a commit;
- reversible or recoverable;
- observable after deployment.

---

## 3. Environment model

Daily Creative supports four logical environments.

## 3.1 Local

Purpose:

- day-to-day development;
- automated integration tests;
- local feature testing;
- API/client development.

Components:

- backend on host or Docker;
- PostgreSQL in Docker;
- MinIO in Docker;
- Descope development project;
- seeded test data;
- iOS simulator or physical device;
- local API URL or secure tunnel for device testing.

Local data is disposable.

## 3.2 Development

Purpose:

- shared integration environment;
- continuous deployment from main branch;
- remote testing by developers;
- integration with real managed services.

Components:

- deployed backend;
- managed PostgreSQL;
- isolated storage bucket;
- Descope development configuration;
- synthetic data;
- automatic migrations through deployment workflow;
- development observability.

Development may be rebuilt or reset.

## 3.3 Staging

Purpose:

- production-like release validation;
- TestFlight release-candidate testing;
- migration rehearsal;
- performance and security verification;
- manual QA.

Components:

- production-equivalent service topology;
- isolated managed PostgreSQL;
- isolated storage;
- separate Descope project/configuration;
- production-like TLS and DNS;
- full monitoring;
- protected deployment workflow;
- realistic synthetic data.

Staging should not use production credentials or live user data.

## 3.4 Production

Purpose:

- live user traffic.

Requirements:

- managed PostgreSQL;
- private object storage;
- production Descope project;
- production backend service;
- restricted administrative access;
- automated backups;
- tested recovery;
- production monitoring and alerts;
- protected deployment;
- auditability.

---

## 4. Environment isolation requirements

Each environment must have unique values for:

- `APP_ENV`;
- API base URL;
- database host and credentials;
- storage endpoint and bucket;
- Descope project ID;
- optional Descope audience override (defaults to project ID);
- logging destination;
- error-monitoring project;
- analytics environment;
- signing credentials;
- feature flags;
- scheduled-job configuration.

Production builds of the iOS app must not be able to silently switch to non-production APIs. Production credentials must never be compiled into non-production builds, and non-production credentials must never be compiled into production builds.

Non-production UI should visibly identify the environment in debug or internal builds.

---

## 5. Recommended production topology

The cloud provider is not mandated.

A suitable topology is:

```text
iOS App
   │
   │ HTTPS
   ▼
Managed DNS
   │
   ▼
Managed TLS ingress / load balancer
   │
   ▼
Stateless FastAPI container service
   │
   ├── Managed PostgreSQL
   ├── Private S3-compatible storage
   ├── Descope
   ├── Logging / metrics / tracing
   └── Scheduled jobs
```

Suitable managed container platforms include:

- Google Cloud Run;
- AWS ECS/Fargate;
- Azure Container Apps;
- Fly.io;
- Render;
- Railway;
- another provider with health checks, TLS, secrets, and private networking.

The initial deployment should use one backend service.

---

## 6. DNS and TLS

Recommended hostnames:

```text
api.dev.dailycreative.example
api.staging.dailycreative.example
api.dailycreative.example
```

Requirements:

- HTTPS only;
- managed certificate renewal;
- HTTP redirected to HTTPS or rejected;
- modern TLS configuration;
- HSTS enabled in production after validation;
- no public database endpoint unless unavoidable and tightly restricted;
- no storage bucket exposed as public website;
- public API hostname stable across deployments.

The backend should trust forwarded headers only from configured ingress infrastructure.

---

## 7. Backend container

## 7.1 Image requirements

The backend container should:

- use a pinned Python base image;
- use a multi-stage build;
- install only production dependencies;
- run as a non-root user;
- contain no secrets;
- expose one application port;
- include build metadata;
- use deterministic dependency locking;
- avoid unnecessary OS packages;
- use a read-only root filesystem where platform support makes this practical.

## 7.2 Suggested Docker build

```text
builder stage
  - install compiler/build dependencies
  - install locked Python dependencies
  - build wheels

runtime stage
  - copy wheels and app
  - install runtime dependencies
  - create non-root user
  - set workdir
  - run Uvicorn
```

## 7.3 Process model

Use Uvicorn directly when the hosting platform manages:

- process restart;
- scaling;
- load balancing;
- health checks.

Begin with one worker per container.

Increase worker count only after measuring:

- CPU utilisation;
- request concurrency;
- database connection usage;
- memory.

## 7.4 Health endpoints

Provide:

```text
GET /health/live
GET /health/ready
```

Liveness:

- confirms process can respond;
- does not require all dependencies.

Readiness:

- confirms database connectivity;
- confirms required configuration;
- may confirm storage configuration without expensive object calls;
- must be fast.

## 7.5 Graceful shutdown

The service must:

- stop accepting new requests;
- complete or cancel in-flight requests within a bounded timeout;
- close database connections;
- flush telemetry where possible.

---

## 8. Application configuration

Use typed settings loaded from environment variables and secret references.

Configuration groups:

### Application

- environment;
- public API URL;
- log level;
- request timeout;
- release version;
- commit SHA;
- Prompt Date timezone;
- allowed image types;
- maximum upload size;
- caption and Reflection limits.

### Database

- connection URL;
- pool size;
- max overflow;
- connection timeout;
- statement timeout;
- SSL mode.

### Descope

- project ID;
- optional audience override (defaults to project ID; issuer/JWKS handled by the official SDK);
- management credentials only where operationally required.

### Storage

- endpoint;
- region;
- bucket;
- access identity;
- signed upload expiry;
- signed read expiry;
- derivative configuration.

### Observability

- error-monitoring DSN;
- tracing endpoint;
- metrics namespace;
- sampling configuration.

### Scheduled jobs

- cleanup retention;
- account-deletion interval;
- prompt-publication schedule;
- orphan-upload threshold.

The backend should fail fast when required production configuration is missing.

---

## 9. Secrets management

Secrets include:

- database password;
- storage credentials;
- Descope management secret;
- administrative API credentials;
- error-monitoring token;
- deployment credentials;
- App Store Connect credentials;
- APNs signing keys if added later.

Requirements:

- never commit secrets;
- never embed private credentials in the iOS app;
- store production secrets in a managed secret service;
- separate secrets by environment;
- restrict access to service identity;
- rotate after suspected exposure;
- redact from logs and CI output;
- avoid passing secrets as Docker build arguments;
- audit access where provider supports it.

Local development uses an ignored `.env` file or local secret manager.

Provide `.env.example` with safe placeholders only.

---

## 10. PostgreSQL infrastructure

## 10.1 Managed service

Staging and production should use managed PostgreSQL.

Requirements:

- encrypted storage;
- TLS connections;
- automated backups;
- point-in-time recovery where available;
- monitoring;
- maintenance windows;
- private networking where supported;
- restricted administrative access.

## 10.2 Version

Use a supported PostgreSQL major version and pin it consistently.

Local Docker and remote environments should use the same major version.

Major upgrades require:

- staging rehearsal;
- migration compatibility review;
- backup verification;
- rollback plan.

## 10.3 Database ownership

Use separate roles:

- migration role;
- application runtime role;
- read-only operational role;
- administrator role.

The runtime role should not own the database or have unrestricted schema privileges.

## 10.4 Connection pooling

Configure SQLAlchemy pool conservatively.

Initial guidance:

- small base pool per instance;
- low overflow;
- bounded acquisition timeout;
- connection recycling;
- statement timeout;
- SSL required remotely.

Total possible connections across all instances must remain below provider limit.

Add PgBouncer or equivalent only if measured need arises.

## 10.5 Migrations

Alembic migrations run as a dedicated release step.

Do not run migrations automatically in each app instance.

Deployment order:

1. build image;
2. run tests;
3. deploy to staging;
4. run staging migration;
5. verify;
6. approve production;
7. verify backup/recovery readiness;
8. run production migration;
9. deploy app;
10. verify health.

Migrations should be backward compatible during rolling deployments.

## 10.6 Backups

Production requirements:

- automated daily backups at minimum;
- point-in-time recovery where available;
- documented retention;
- backup failure alerts;
- encrypted backup storage;
- restricted access;
- periodic restore testing.

A backup is not considered reliable until restored successfully.

## 10.7 Restore tests

At least quarterly for early production, and more often before risky migrations:

1. restore latest backup into isolated environment;
2. apply required migrations;
3. verify Prompt, user, feed, profile, Like, and Reflection queries;
4. verify storage references;
5. record recovery duration and findings.

## 10.8 Data retention

Document retention for:

- active user data;
- deleted accounts;
- deleted Submissions;
- removed content;
- reports;
- activity events;
- idempotency keys;
- expired Sketch Sessions;
- upload records;
- audit logs.

Retention must align with privacy policy.

---

## 11. Object storage

## 11.1 Bucket isolation

Recommended:

```text
dailycreative-dev-media
dailycreative-staging-media
dailycreative-production-media
```

Separate cloud projects/accounts are preferable when practical.

## 11.2 Privacy

Buckets are private.

The public must not have list or direct permanent read access.

## 11.3 Object keys

Use opaque UUID-based keys.

Example:

```text
users/{user_uuid}/uploads/{upload_uuid}/original
users/{user_uuid}/uploads/{upload_uuid}/display
users/{user_uuid}/uploads/{upload_uuid}/thumbnail
users/{user_uuid}/avatars/{upload_uuid}/display
```

Do not use:

- username;
- caption;
- email;
- Prompt words;
- original local path.

## 11.4 Service identity permissions

Backend needs only:

- create signed upload URL;
- read object metadata;
- read/write derivatives;
- delete scoped objects;
- optionally list a narrow prefix for reconciliation.

The iOS app never receives permanent credentials.

## 11.5 Signed uploads

Signed upload URLs should:

- expire quickly;
- target exactly one key;
- allow one HTTP method;
- restrict content type where supported;
- restrict size where supported;
- not permit list or read;
- not expose bucket credentials.

## 11.6 Signed reads or CDN

Version one may use:

- short-lived signed read URLs.

Later:

- CDN-backed stable URLs;
- image-transformation service;
- protected origin.

The API must not expose internal storage keys.

## 11.7 Lifecycle policies

Configure cleanup for:

- pending uploads never completed;
- failed processing objects;
- orphaned derivatives;
- deleted-account media;
- temporary processing files;
- old object versions if versioning enabled.

## 11.8 Object versioning

Production may enable versioning or soft-delete retention to protect against accidental deletion.

Balance with:

- privacy deletion;
- storage cost;
- operational simplicity.

Document how final deletion is completed.

---

## 12. Image processing infrastructure

Version one should avoid a separate worker if bounded synchronous processing is reliable.

Options:

### Option A — synchronous backend processing

Suitable when:

- uploads have strict size limits;
- derivative generation is quick;
- request timeout allows it.

Risks:

- higher request latency;
- container CPU spikes;
- failure during deployment/restart.

### Option B — managed image service

Suitable when provider offers:

- private-source support;
- derivative generation;
- CDN;
- metadata stripping.

### Option C — durable worker

Introduce only if processing must survive process restarts or scale independently.

Version-one recommendation:

- synchronous or managed processing;
- no Redis/queue;
- strict limits;
- metrics on processing time/failure.

---

## 13. Local development infrastructure

Docker Compose should include:

```text
postgres
minio
backend
```

Optional:

- migration one-shot;
- database admin UI;
- OpenTelemetry collector.

Recommended commands:

```text
make up
make down
make logs
make seed
make db-migrate
make db-reset
make test
make clean-local
```

Local `make up` merges `docker-compose.override.yml`: bind-mounted backend sources, dependency sync, migrate-on-start, and uvicorn `--reload`.

Requirements:

- named volumes;
- documented ports;
- health checks;
- deterministic startup;
- warning before destructive reset;
- local bucket bootstrap;
- development CORS/configuration if needed.

For physical iPhone testing:

- use local-network hostname or secure tunnel;
- document ATS/TLS implications;
- do not weaken production transport security.

---

## 14. Infrastructure as code

Use one of:

- Terraform;
- OpenTofu;
- Pulumi;
- provider-native declarative tooling.

It should manage:

- container service;
- database;
- storage buckets;
- service identities;
- network rules;
- DNS;
- TLS;
- secret references;
- logging sinks;
- alerts;
- scheduled jobs;
- environment variables.

Infrastructure state must be:

- remote;
- encrypted;
- access controlled;
- separated by environment;
- locked during changes.

Production infrastructure changes require review.

Avoid manual console configuration except bootstrap actions that are documented.

---

## 15. Continuous integration

GitHub Actions is the reference CI implementation for the initial repository unless an existing repository has already standardised on another capable provider. Changing CI provider does not change the required checks in this specification.

CI runs on every pull request.

## 15.1 Backend checks

- dependency installation;
- OpenAPI validation;
- generated-client drift;
- Ruff lint;
- formatting;
- type checking;
- unit tests;
- PostgreSQL integration tests;
- MinIO/storage tests;
- migration apply on clean database;
- contract tests;
- Docker build;
- vulnerability scan where practical.

## 15.2 iOS checks

- project generation/resolution if applicable;
- simulator build;
- unit tests;
- selected UI tests;
- generated API client drift;
- SwiftLint if adopted;
- no production secrets in app bundle.

## 15.3 Repository checks

- secret scanning;
- dependency alerts;
- prohibited large files;
- spec presence;
- migration naming/ordering checks;
- licence checks where needed.

## 15.4 CI data

Use ephemeral PostgreSQL and MinIO.

Tests must not depend on shared development services.

---

## 16. Continuous deployment

## 16.1 Development

Recommended:

- automatic deploy from main branch;
- migration step included;
- smoke test after deployment;
- rollback on failed health check.

## 16.2 Staging

Recommended:

- deploy immutable release candidate;
- protected approval or release branch/tag;
- run migrations;
- run automated smoke/end-to-end tests;
- distribute matching TestFlight build.

## 16.3 Production

Requirements:

- explicit approval;
- same backend image tested in staging;
- release metadata recorded;
- migrations run explicitly;
- health verification;
- monitoring during rollout;
- documented rollback.

Do not rebuild materially different artifacts between staging and production.

---

## 17. Deployment strategy

Use rolling or blue/green deployment where provider supports it.

Requirements:

- readiness before traffic;
- graceful termination;
- migration compatibility;
- no routine downtime;
- automatic rollback on failed health checks where possible.

The App Store creates client-version overlap.

Backend must tolerate supported older iOS versions.

---

## 18. Release metadata

Expose internally:

- app version;
- API version;
- commit SHA;
- build timestamp;
- environment;
- migration revision.

A protected diagnostic endpoint may expose safe metadata.

Do not expose infrastructure credentials, topology, or provider internals publicly.

---

## 19. OpenAPI delivery pipeline

CI must:

1. validate `openapi.yaml`;
2. detect unresolved references;
3. check backward compatibility where practical;
4. generate Swift client;
5. fail on generated drift;
6. run backend contract tests;
7. publish rendered docs for non-production environments if useful.

The deployed backend release should be traceable to an exact contract revision.

---

## 20. iOS build and distribution

## 20.1 Project identifiers and release prerequisites

Canonical project settings:

- app display name: **Daily Sketch**;
- primary Xcode product/module name: `DailySketch`;
- minimum supported operating system: **iOS 18.0**.

The production bundle identifier and Apple Developer Team ID remain deployment-specific values and must not be invented or hard-coded throughout the project. Until the owner supplies final values:

- define bundle identifiers centrally through `.xcconfig` or equivalent build settings;
- use clearly marked non-production placeholders such as `com.example.dailysketch.dev`;
- keep Development, Staging, and Production bundle identifiers distinct;
- inject the Apple Team ID through local or CI signing configuration;
- never commit signing certificates, provisioning profiles, private keys, or App Store Connect secrets.

Before production release, the owner must provide and verify:

- final production bundle identifier;
- Apple Developer Team ID;
- App Store Connect application record;
- support URL;
- privacy-policy URL;
- terms URL;
- production Descope configuration;
- production API hostname.

The production cloud provider is intentionally provider-neutral in version one. A provider may be selected during infrastructure implementation without changing the application architecture, provided it satisfies this specification.

## 20.2 Build configurations

Support:

- Debug Local;
- Debug Development;
- Release Staging;
- Release Production.

Each defines:

- API base URL;
- public Descope configuration;
- logging level;
- analytics environment;
- feature flags;
- environment badge for non-production.

## 20.3 Signing

Protect:

- certificates;
- provisioning profiles;
- App Store Connect keys;
- production signing access.

Production signing should not be available to untrusted pull-request jobs.

## 20.4 TestFlight

Use TestFlight for:

- internal development builds;
- staging release candidates;
- external beta.

Release records should map:

- iOS build;
- backend version;
- API contract;
- migration revision.

## 20.5 Minimum iOS version

The deployment target is **iOS 18.0** for every application, unit-test, UI-test, and supporting target. CI must detect target drift. Raising the minimum version requires an explicit product decision and an update to the specifications.

---

## 21. Logging

Use structured JSON logging remotely.

Each request log includes:

- request ID;
- method;
- route template;
- status;
- latency;
- environment;
- release version;
- internal user UUID where safe;
- stable error code.

Do not log:

- JWTs;
- signed URLs;
- passwords;
- email addresses by default;
- image bytes;
- full captions;
- Reflection bodies;
- Draft content;
- Descope secrets;
- storage credentials.

Use sampling for noisy success logs if volume grows.

---

## 22. Metrics

## 22.1 Infrastructure metrics

Track:

- container CPU;
- memory;
- restart count;
- instance count;
- request concurrency;
- database CPU;
- database storage;
- database connections;
- object storage usage;
- bandwidth;
- scheduled-job outcomes.

## 22.2 API metrics

Track:

- request count;
- latency by route;
- 4xx/5xx rates;
- authentication failures;
- feed latency;
- profile latency;
- Like/Reflection write latency;
- upload-slot creation;
- upload verification;
- Submission creation;
- account deletion.

## 22.3 Product funnel metrics

Operational platform may emit privacy-safe events for:

- Prompt viewed;
- Sketch Session started;
- Review shown;
- Draft saved;
- upload started/completed;
- Submission published;
- Like;
- Reflection;
- profile view;
- reminder enabled.

Do not include user-generated text or raw image URLs.

---

## 23. Tracing

Use OpenTelemetry-compatible tracing.

Important spans:

- JWT verification;
- user provisioning;
- database transaction;
- Prompt lookup;
- feed query;
- upload signing;
- object verification;
- derivative processing;
- Submission creation;
- Like/Reflection transaction;
- account deletion.

Use trace sampling appropriate to environment.

Errors should retain traces.

---

## 24. Error monitoring

Use backend and iOS error monitoring.

Capture:

- unhandled exceptions;
- iOS crashes;
- non-fatal upload/publication failures;
- release version;
- environment;
- request ID;
- device/OS metadata within privacy limits.

Minimise user-identifying data.

Configure alert grouping and release tracking.

---

## 25. Dashboards

At minimum, production dashboard should show:

- availability;
- request rate;
- p50/p95/p99 latency;
- error rate;
- database health;
- connection pool;
- upload success/failure;
- image-processing failure;
- Submission creation success;
- Like/Reflection errors;
- scheduled-job status;
- recent deployments.

A separate product dashboard may show:

- session funnel;
- publication conversion;
- social activity;
- retention.

---

## 26. Alerting

Alerts must be actionable.

Alert on:

- backend unavailable;
- sustained elevated 5xx;
- sustained latency regression;
- database unavailable;
- database storage near capacity;
- connection exhaustion;
- backup failure;
- migration failure;
- object storage access failure;
- high upload failure rate;
- high derivative-processing failure;
- scheduled cleanup failure;
- missing future Prompt;
- account-deletion backlog;
- deployment health failure.

Avoid paging on isolated expected client errors.

Every alert needs:

- severity;
- owner;
- runbook;
- threshold;
- recovery condition.

---

## 27. Scheduled jobs

Version one requires scheduled work but not a persistent queue.

Use provider scheduler or managed cron jobs.

Jobs include:

### Prompt management

- generate future Prompts;
- publish Prompt;
- detect missing tomorrow Prompt.

### Upload cleanup

- expire pending uploads;
- remove orphan objects;
- reconcile database/storage.

### Sketch Session cleanup

- expire stale active sessions;
- preserve analytics state.

### Draft cleanup

Local iOS handles local Draft cleanup.

Server does not manage guest local Drafts.

### Account deletion

- process pending deletions;
- remove media;
- coordinate Descope deletion;
- finalise status.

### Media cleanup

- remove deleted Submission images after retention;
- remove failed derivatives.

### Idempotency cleanup

- remove expired idempotency records.

Requirements:

- idempotent;
- retryable;
- observable;
- safe under duplicate execution;
- concurrency protected where needed;
- dry-run support for destructive cleanup.

---

## 28. Prompt publication operations

Prompts should be generated ahead of time.

Operational requirements:

- curated source word list;
- at least several weeks of future Prompts;
- no duplicate words within Prompt;
- one Prompt per date;
- validation before publication;
- audit correction after publication;
- alert if tomorrow is missing.

If current Prompt is missing:

- backend returns explicit error;
- app does not invent a prompt;
- operator can publish correction.

---

## 29. Moderation operations

Version one may use protected commands or internal endpoints.

Operators need ability to:

- list reports;
- inspect target metadata;
- hide/remove Submission;
- hide/remove Reflection;
- suspend user;
- restore content;
- record reason.

Requirements:

- named operator identity;
- audit trail;
- least privilege;
- no casual direct DB edits;
- secure access;
- no exposure of unnecessary personal data.

---

## 30. Administrative access

Use individual accounts.

Require MFA for:

- cloud provider;
- source control;
- Descope admin;
- App Store Connect;
- DNS registrar;
- production database access;
- error-monitoring platform.

Production database access:

- read-only by default;
- time-limited elevation;
- recorded reason;
- named identity;
- audited where possible.

Avoid SSH into production containers.

---

## 31. Security controls

## 31.1 Network

- HTTPS only;
- private database;
- private bucket;
- restricted administrative endpoints;
- minimal ingress ports;
- no public MinIO/admin consoles;
- outbound access restricted where practical.

## 31.2 Identity and IAM

- unique engineer accounts;
- MFA;
- least privilege;
- separate service identities;
- no shared root credentials;
- periodic access review;
- remove access promptly when no longer needed.

## 31.3 Dependency security

Automate:

- Python dependency alerts;
- Swift dependency alerts;
- base image updates;
- container scanning;
- secret scanning;
- licence awareness.

Critical vulnerabilities should block release unless explicitly accepted.

## 31.4 Application protection

Infrastructure should support:

- request-size limits;
- image-size limits;
- rate limiting;
- abuse detection;
- secure headers;
- log redaction;
- audit logging;
- moderation actions.

## 31.5 Storage protection

- private by default;
- short-lived signed URLs;
- non-guessable keys;
- no public list access;
- EXIF removal;
- lifecycle cleanup.

---

## 32. Privacy operations

Infrastructure must support:

- account deletion;
- image deletion;
- public profile removal;
- report retention;
- minimal audit retention;
- data export later if required;
- environment isolation;
- access controls;
- retention documentation.

Do not collect precise location.

Do not retain raw EXIF location.

Do not include user-generated content in operational telemetry.

---

## 33. Backup and disaster recovery

## 33.1 Suggested initial objectives

For early beta:

- RPO: up to 24 hours at minimum, improved through PITR;
- RTO: several hours.

Review before significant growth.

## 33.2 Recovery procedure

Document:

1. declare incident;
2. stop harmful writes if necessary;
3. identify restore point;
4. restore database;
5. verify object storage consistency;
6. deploy compatible backend version;
7. apply migrations if needed;
8. validate Descope configuration;
9. run smoke tests;
10. resume traffic;
11. communicate impact.

## 33.3 Object consistency

Database restore may reference media created after restore point or miss references to objects.

Provide reconciliation tooling to:

- find orphan objects;
- find missing objects;
- report inconsistencies;
- avoid destructive automatic cleanup immediately after restore.

---

## 34. Incident response

For production incidents:

1. assign severity;
2. assign incident owner;
3. preserve logs and evidence;
4. mitigate;
5. communicate;
6. recover;
7. document timeline and cause;
8. create follow-up actions.

Security incidents may require:

- credential rotation;
- access review;
- user notification;
- legal/privacy assessment;
- provider escalation.

Maintain incident records outside chat history.

---

## 35. Cost controls

Use budget alerts.

Track cost drivers:

- managed database;
- container runtime;
- object storage;
- image egress;
- logs;
- metrics/traces;
- error monitoring;
- Descope usage;
- TestFlight/build infrastructure.

Controls:

- small initial database tier;
- bounded autoscaling;
- upload/image size limits;
- storage lifecycle rules;
- log retention;
- staging scale-down where possible;
- tracing sample limits.

Do not reduce backups or security to save small amounts.

---

## 36. Capacity planning

Monitor:

- feed query latency;
- profile query latency;
- database CPU;
- connections;
- storage growth;
- image bandwidth;
- upload concurrency;
- processing time;
- container memory;
- scheduled-job duration.

Scale in this order:

1. optimise SQL and indexes;
2. tune pool/timeouts;
3. increase database capacity;
4. add backend instances;
5. add CDN/image service;
6. add durable worker if needed;
7. add Redis only for measured hot paths.

Do not introduce caching to hide inefficient queries.

---

## 37. Feature flags

Use a minimal environment-specific mechanism.

Possible flags:

- new Home layout;
- social Activity UI;
- APNs notifications;
- image-processing path;
- moderation UI;
- beta feature visibility.

Requirements:

- safe default;
- removable;
- documented;
- not used to bypass API versioning;
- production changes auditable.

---

## 38. Release process

Production release:

1. merge reviewed code;
2. CI passes;
3. build immutable image;
4. validate OpenAPI compatibility;
5. deploy to staging;
6. run staging migrations;
7. run smoke/end-to-end tests;
8. validate TestFlight build;
9. approve release;
10. verify backup/recovery readiness;
11. run production migration;
12. deploy backend;
13. verify health/metrics;
14. release or phase iOS build;
15. monitor;
16. record release notes.

---

## 39. Rollback strategy

Rollback must consider application and database.

Options:

- deploy previous image;
- disable feature flag;
- retain backward-compatible schema;
- roll forward with corrective migration;
- restore database only under incident process.

Avoid irreversible destructive migrations while old iOS clients remain supported.

Database rollback is not the default response to application failure.

---

## 40. Runbooks

Create runbooks for:

- backend unavailable;
- database connection failure;
- backup failure;
- storage failure;
- upload spike;
- image-processing failures;
- missing Daily Prompt;
- migration failure;
- account-deletion backlog;
- report/moderation incident;
- credential exposure;
- iOS/backend contract incompatibility.

Each runbook includes:

- symptoms;
- checks;
- mitigation;
- escalation;
- recovery;
- follow-up.

---

## 41. Infrastructure acceptance criteria

Infrastructure is production-beta ready when:

- local setup is reproducible;
- environments are isolated;
- backend is stateless;
- production PostgreSQL is managed and backed up;
- restore test has succeeded;
- object storage is private;
- signed upload/read flow works;
- orphan cleanup exists;
- secrets are externalised;
- CI validates contract, code, migrations, tests, and container;
- staging and production deployments are protected;
- health checks work;
- logs, metrics, tracing, and errors are visible;
- actionable alerts exist;
- scheduled jobs are observable;
- account deletion is operational;
- rollback is documented;
- TestFlight and backend releases are traceable;
- no Redis, queue, or Kubernetes dependency exists without ADR.

---

## 42. Future infrastructure evolution

Possible later additions:

- CDN;
- managed image transformation;
- durable background worker;
- APNs push service;
- Activity inbox processing;
- Redis;
- read replicas;
- analytics warehouse;
- moderator web app;
- regional deployment;
- advanced rate limiting;
- multi-region disaster recovery.

Each addition must be justified by observed need and recorded in an ADR.

---

## 43. Canonical infrastructure decisions

- App display name is Daily Sketch; primary module name is `DailySketch`; minimum iOS version is 18.0.
- Bundle identifiers and Apple signing identifiers are centrally configured and supplied by the owner before production release.
- GitHub Actions is the reference CI implementation unless the repository already has an equivalent provider.
- Four environments: local, development, staging, production.
- Managed PostgreSQL for staging and production.
- S3-compatible private object storage.
- One stateless FastAPI service.
- Docker-based backend deployment.
- Infrastructure as code.
- Explicit Alembic release migrations.
- OpenAPI validation and generated-client drift in CI.
- Automatic development deployment; protected staging/production.
- Local notifications in version one.
- Scheduled provider jobs instead of a queue.
- Structured logs, metrics, tracing, and error monitoring.
- Automated backups with tested restore.
- No Redis, Kubernetes, or worker service in version one.
