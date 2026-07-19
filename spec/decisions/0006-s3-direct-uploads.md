# 0006 — S3 Direct Signed Uploads

- Status: Accepted
- Date: 2026-07-18
- Deciders: Engineering

## Context

Submissions require user-generated images. Proxying large binaries through the API increases latency, memory pressure, and bandwidth cost. The architecture calls for direct client uploads to private object storage with short-lived signed URLs.

## Decision

Clients request an upload slot (`POST /api/v1/uploads`), receive a short-lived signed `PUT` URL, upload bytes directly to MinIO/S3-compatible storage (via boto3-generated signatures), then call `POST /api/v1/uploads/{id}/complete`. The API records object keys and metadata; media bytes never transit the API process on the write path. `STORAGE_PUBLIC_ENDPOINT` lets signed URLs target a host-reachable endpoint while server-side boto3 calls use the internal endpoint.

## Consequences

- Upload slots expire; incomplete uploads need eventual cleanup (deferred with orphan jobs).
- Integration tests use an in-memory fake storage adapter; optional MinIO adapter tests run when `STORAGE_TEST=1`.
- Changing to a CDN or multiparty upload flow requires a new ADR.
