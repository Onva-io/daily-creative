# 0001 — Monorepo structure

- Status: Accepted
- Date: 2026-07-18
- Deciders: Engineering

## Context

Daily Sketch requires a native iOS client, a FastAPI backend, an OpenAPI contract, and shared specifications. Coordinating these across separate repositories increases friction for contract-first delivery and phase-gated implementation.

## Decision

Use a single monorepo with top-level packages:

- `api/` — OpenAPI source of truth and generated clients
- `backend/` — FastAPI application, migrations, and tests
- `ios/` — SwiftUI application and tests
- `spec/` — product, design, architecture, implementation, and infrastructure specifications

## Consequences

- Contract, backend, and client changes can land in one pull request when needed.
- CI must cover multiple platforms (Python and Xcode).
- Generated OpenAPI client output lives under `api/generated/` and must not be hand-edited.
