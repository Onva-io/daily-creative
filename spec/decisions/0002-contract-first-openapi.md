# 0002 — Contract-first OpenAPI

- Status: Accepted
- Date: 2026-07-18
- Deciders: Engineering

## Context

Mobile clients and the backend must share a stable HTTP API. Generating documentation from FastAPI handlers after implementation makes the backend the de facto contract and risks client drift.

## Decision

`api/openapi/openapi.yaml` is the API source of truth. For every API-backed feature:

1. update the OpenAPI contract;
2. validate the contract;
3. generate or update the Swift client;
4. implement backend handlers and tests;
5. integrate the iOS client.

FastAPI may validate conformance, but handlers are not the primary documentation workflow. Generated client code must never be edited manually.

## Consequences

- CI fails when generated clients are stale.
- Additive versioning discipline is required for App Store client overlap.
- Feature work begins with contract changes, not route implementations.
