# 0010 — Guest Age Gate Before Community Content

- Status: Accepted
- Date: 2026-07-30
- Updated: 2026-08-13
- Deciders: Engineering

## Context

Product §33 intentionally allows unauthenticated browsing of the Daily Prompt, public feed, submission detail, and public profiles. For a social UGC app that minors may use, that means a signed-out underage user can view community content without any age declaration or policy acceptance. Apple Guideline 1.2 and regional age-assurance expectations make that a launch risk.

A client-only overlay (UserDefaults date of birth) is not enough: anyone can call the public GETs, and reinstall or editing defaults bypasses the gate.

## Decision

1. Keep first launch frictionless: the Daily Prompt and app shell remain available without authentication.
2. Require a **server-issued** guest age token before community payloads (feed, submission detail, public profiles, reflections) for anonymous callers.
3. `POST /api/v1/guest/age-declaration` verifies date of birth against the published terms minimum age and returns an HMAC-signed capability token. The date of birth is **not stored** for guests and is not embedded in the token.
4. Community GETs accept either a valid Descope bearer token or `X-Guest-Age-Token`.
5. Clients persist guest date of birth and the capability token in Keychain (this-device-only), not UserDefaults. On signup, reconcile the on-device DOB via `POST /api/v1/me/date-of-birth`.
6. Authenticated users continue to be gated by server-side consent (`consent_required` on `/me`) for policies and age.

## Consequences

- Revises the prior “fully public community without any gate” interpretation of §33.
- Clients must show an age gate overlay before community tabs/content load for guests, and must send the server token on community GETs.
- Staging/production require a unique `GUEST_AGE_TOKEN_SECRET` (32+ characters). The local default is rejected remotely.
- Direct API clients must declare age before reading community content; scraping the feed without a token returns `403 age_declaration_required`.
