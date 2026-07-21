# Daily Story — Product Specification

## Overview

Daily Story is a companion app to Daily Sketch, sharing the same backend API, user accounts, and daily three-word prompts. Instead of sketching, users write short stories inspired by the daily prompt.

## Core Flow

1. **Open the app** → See today's three-word prompt
2. **Tap "Start Writing"** → Choose a timer duration (or no timer)
3. **Timer phase** → Think about your story while the timer counts down. You can pause, resume, or finish early.
4. **Writing phase** → After the timer completes (or you finish early), a text editor opens for writing your story.
5. **Review & Publish** → Preview your story, add an optional caption, and publish to the community feed.

## Timer Options

Same as Daily Sketch:
- 1 minute
- 3 minutes
- 5 minutes (default)
- 10 minutes
- No timer

## Story Session Lifecycle

```
active → paused → active (resumed)
active → writing (timer_completed / finished_early / writing_started)
writing → writing (draft_saved — stays in writing)
writing → completed (submission_created)
any non-terminal → abandoned
any non-terminal → expired (after 24h)
```

### Status Machine

| Status | Description |
|--------|-------------|
| `active` | Timer is running (or prompt contemplation for no-timer mode) |
| `paused` | Timer paused by user |
| `writing` | Timer done; user is composing their story |
| `completed` | Story published as a submission |
| `abandoned` | User explicitly abandoned the session |
| `expired` | Session auto-expired after 24 hours |

## Submission

- `creative_type`: `story`
- `body`: Full story text (required, max 10,000 characters)
- `caption`: Optional (max 280 characters)
- No image upload required (unlike sketch)
- `story_session_id` links the submission to the session

## Feed Display

Story submissions appear in the community feed alongside sketches:
- Card shows a text preview (`body_preview`) instead of a thumbnail
- Word count displayed
- Same like/reflection/share functionality as sketches
- Feed can be filtered by `creative_type` query parameter

## Profile & Streaks

- Submission counts and streaks are scoped by `creative_type`
- A user can maintain separate streaks for sketches and stories
- Profile gallery can be filtered by creative type

## Differences from Daily Sketch

| Feature | Daily Sketch | Daily Story |
|---------|-------------|-------------|
| Creative output | Image (camera/photo) | Text (editor) |
| Upload required | Yes | No |
| Camera permission | Required | Not needed |
| Session-specific statuses | `ready_for_photo`, `uploading` | `writing` |
| Draft storage | Image file on device | Text in UserDefaults |
| Feed card display | Thumbnail image | Text preview + word count |

## Future Considerations

- Text moderation / content filtering for story submissions
- Rich text formatting (bold, italic) — currently plain text only
- Word count limits or targets
- Writing streak challenges
- Story collections / series
