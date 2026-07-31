# 0011 — Submission Prompt Date window

- Status: Accepted
- Date: 2026-07-31
- Deciders: Engineering

## Context

A Sketch or Story Session binds to a `prompt_id` at create time, and Submissions inherit that Prompt Date. Clients may start work near UTC midnight, cross into the next Prompt Date with a timer still running, and publish afterwards. Drafts may also create the server Session lazily at publish time.

Without an upper bound on how old a Prompt may be, a client can publish against an arbitrarily old Prompt Date and retroactively repair a broken streak. Client-supplied start timestamps cannot gate that decision: they are under the client's control and the codebase already treats `client_occurred_at` and `client_timezone` as audit metadata only (ADR 0005 keeps Prompt Date server-authoritative UTC).

`compute_current_streak` already returns zero when the latest Prompt Date is older than yesterday. The submission path must enforce the same bound.

## Decision

Submissions and Session creates may only target a Prompt whose `prompt_date` is **today or yesterday** in UTC, measured by the server clock at request time. Future Prompt Dates are also rejected (tomorrow's Prompt may already exist via pre-seeding).

- Window size is configured as `SUBMISSION_BACKDATE_DAYS` (default `1`).
- Rejection code: `422 prompt_date_out_of_window`.
- `POST /submissions` requires a declared `prompt_id` that must equal the Session's `prompt_id`; mismatch yields `409 prompt_mismatch`. The declared id is verification only — the Session remains the source of truth for dating.
- Optional `client_started_at` on Session create is stored in started metadata for audit and never used for expiry or Prompt Date decisions.
- Existing 24-hour Session expiry remains complementary: it bounds in-flight Sessions; the Prompt Date window bounds which day a Session may target.

## Consequences

- A 23:55 start that publishes at 00:05 against yesterday's Prompt succeeds.
- A week-old draft cannot invent a fresh Session for its stale Prompt at publish time.
- Streak calculation and submission eligibility stay aligned on the same today/yesterday UTC bound.
- Changing the window requires updating `SUBMISSION_BACKDATE_DAYS`, the streak invariant, this ADR, and product copy together.
