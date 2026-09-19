# Daily Photo — Product Specification

## Overview

Daily Photo is a companion app to Daily Sketch and Daily Story, sharing the same backend API, user accounts, and daily three-word prompt. Instead of drawing or writing, the user goes and finds today's words through a camera lens, then shares one photograph and, optionally, where it was taken.

It is a daily creative practice, not a photo-sharing network. There is no map of everyone's photos, no "nearby", no place pages, no follow graph, no filters, and no "more like this". The only way a location appears in the product is attached to one post, as the author wrote it.

## Core Flow

1. **Open the app** → See today's three-word prompt
2. **Tap "Take Photo"** → The timer picker opens on **No timer** (a photograph is usually taken when the moment comes); any countdown can still be chosen and remembered
3. **Timer phase (optional)** → Look for the shot while the timer runs; pause, resume, or finish early
4. **Capture** → Take a photo with the camera or choose one from the library
5. **Review** → Preview the image, add an optional caption, confirm the location (see below), and publish or save to Drafts

Steps 1–5 are the shared capture flow used by Daily Sketch. Daily Photo adds only the location editor on the review screen.

## Timer Options

Same options as the other apps: 1, 3, 5, 10 minutes, or No timer. Daily Photo's default preselection is **No timer**. The remembered choice is stored per app (`creative_type_preferences`), so a Daily Photo preference never changes Daily Sketch or Daily Story.

## Location

Location is optional, explicit, and author-controlled.

### Seeding (automatic suggestion)

When a new image enters the flow the app suggests a place, in this order:

1. **The photo's own location** — EXIF GPS read on-device from the picker's original bytes (library picks only; camera captures have none).
2. **The device's current location** — one when-in-use fix, requested at that moment with a clear purpose string. Denied or unavailable simply means no suggestion.
3. **Nothing** — the editor is empty.

Seeding never blocks review; a slow device fix is abandoned after ~12 seconds and never overrides something the author has already chosen.

### Author overrides

- **Search** for a place (Apple Maps local search); choosing a result sets the pin and, if the title is empty, fills it with the place name.
- **Tap the map** to move the pin anywhere.
- **Place title** — a free-text label (max 120 characters), the author's own words ("Brighton seafront", "Grandma's kitchen"). This is what other people see by default.
- **Remove location** clears everything.

Replacing the image re-seeds a location that was suggested automatically (EXIF/device) but leaves an author-chosen one (search/pin) alone.

### Sharing exact location — per post, off by default

A **Share exact location** toggle on the review screen decides what other users receive:

| Toggle | Other users see | The author sees |
|--------|-----------------|-----------------|
| Off (default) | Place title only; no coordinates are returned by the API | Title, coordinates, map |
| On | Place title and coordinates, rendered as a single non-interactive map on the detail screen | Same |

The toggle is unavailable until there are coordinates. The choice is stored with the post and applies only to that post. The coordinate `source` (EXIF/device/search/pin) is kept for audit and is never returned to any client.

### What the platform does not do

- No reverse geocoding, geohashing, clustering, or place index on the server
- No location-based feed, filter, ranking, or discovery
- No background location; permission is when-in-use only, asked at review time
- Uploaded image bytes never carry EXIF GPS (the client re-encodes the JPEG)

## Session Lifecycle

Identical to Daily Sketch (both use the shared capture stage rules):

```
active → paused → active (resumed)
active → ready_for_photo (timer_completed / finished_early / photo_step_reached)
ready_for_photo → uploading (upload_started / upload_completed)
uploading → completed (submission_created)
any non-terminal → abandoned   (not from uploading)
any non-terminal → expired     (after 24h; ready_for_photo/uploading exempt)
```

## Submission

- `creative_type`: `photo`
- `content.upload_id`: the uploaded JPEG (required)
- `content.caption`: optional (max 280 characters)
- `content.location`: optional object — `latitude`/`longitude` (as a pair), `label` (max 120), `source`, `share_exact` (default false). Coordinates alone, a label alone, or both are valid; `share_exact` requires coordinates.

## Feed and Detail Display

- Feed card: image, then a one-line pin + place title when the author gave one
- Detail: image, pin row, and — only when coordinates were shared with this viewer — a small static map with one marker
- Profile gallery: image only
- Same like / reflection / share / report behaviour as other types
- The author-written place title is included in text moderation

## Drafts

The local draft stores the location alongside the caption (`LocalDraft.contentExtras`, opaque to the shared shell). Reopening a draft restores the author's location and sharing choice without asking the device again. Guests keep their draft and location through sign-in at the publish checkpoint.

## Account deletion and post deletion

Deleting a post removes its location with it. Account deletion redacts the whole `location` object (coordinates and title) as personal data.

## Differences from Daily Sketch

| Feature | Daily Sketch | Daily Photo |
|---------|-------------|-------------|
| Creative output | Photo of an off-phone drawing | Photograph |
| Default timer | Must choose | No timer preselected |
| Location | None | Optional, author-confirmed, per-post exact sharing |
| Permissions | Camera, Photo Library | Camera, Photo Library, Location (when in use) |
| Review screen | Image + caption | Image + caption + location editor |
| Privacy manifest | — | Adds Precise Location (linked, not tracking) |

## Future Considerations

- Coarse ("neighbourhood") sharing as a third option between title-only and exact
- Draggable pin annotation (currently tap-to-move)
- Reading capture time from EXIF to suggest an "early morning" style note (never shown automatically)
