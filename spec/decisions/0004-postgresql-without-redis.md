# 0004 — PostgreSQL without Redis

- Status: Accepted
- Date: 2026-07-18
- Deciders: Engineering

## Context

Version one needs durable application state for users, prompts, sessions, submissions, likes, and reflections. Early-stage traffic does not justify a distributed cache or queue topology.

## Decision

PostgreSQL is the durable system of record for application state (except media bytes). Version one does not introduce Redis, Kafka, SQS, Celery, or microservices. The feed is reverse-chronological and query-backed. Object storage holds media; the backend remains one stateless FastAPI service.

## Consequences

- Indexes and query plans must be measured before adding caches.
- Scheduled provider jobs handle cleanup instead of a durable worker queue.
- Adding Redis later requires measured need and an ADR.
