# 0010 — Guest Age Gate Before Community Content

- Status: Accepted
- Date: 2026-07-30
- Deciders: Engineering

## Context

Product §33 intentionally allows unauthenticated browsing of the Daily Prompt, public feed, submission detail, and public profiles. For a social UGC app that minors may use, that means a signed-out underage user can view community content without any age declaration or policy acceptance. Apple Guideline 1.2 and regional age-assurance expectations make that a launch risk.

## Decision

1. Keep first launch frictionless: the Daily Prompt and app shell remain available without authentication.
2. Require a local age declaration (date of birth) **before rendering community content** (feed, submission detail, public profiles) for guests.
3. Persist the guest declaration on-device and reconcile it to the account on signup via `POST /api/v1/me/date-of-birth`.
4. Authenticated users continue to be gated by server-side consent (`consent_required` on `/me`) for policies and age.

## Consequences

- Revises the prior “fully public community without any gate” interpretation of §33.
- Clients must show an age gate overlay before community tabs/content load for guests.
- Backend public endpoints remain optionally authenticated; the gate is enforced primarily on the client for guests, and server-side for authenticated mutating/authenticated gated routes.
