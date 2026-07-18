# Daily Sketch — Design Specification

**Version:** 1.1
**Status:** Canonical design and interaction baseline
**Primary platform:** Native iOS using SwiftUI
**Visual reference:** `stitch_daily_sketch_journal.zip`

## 1. Purpose of this document

This document defines how Daily Sketch should look, feel, navigate, and respond to user input.

It is intended to give Cursor and a human iOS developer enough direction to implement the first production version without inventing core UX decisions. It covers:

- visual language and design tokens;
- navigation structure;
- screen composition;
- interaction behaviour;
- reusable components;
- loading, empty, error, and success states;
- accessibility and responsive behaviour;
- the relationship between the Stitch export and the product specification.

`product.md` remains authoritative for product scope and business behaviour. This file is authoritative for the intended presentation and interaction of that behaviour. `architecture.md` controls technical boundaries and `implementation.md` controls delivery order.

The Stitch export is a strong visual starting point, not an infallible behavioural specification. Where its copy or controls conflict with `product.md`, the corrected behaviour in this document must be used.

---

## 2. Stitch reference inventory

The supplied archive contains the following useful visual references when unpacked:

```text
stitch_daily_sketch_journal/
├── home_today_s_inspiration/screen.png
├── home_fanned_inspiration/screen.png
├── timer_selection_fixed/screen.png
├── sketch_session/screen.png
├── confirm_submission/screen.png
├── save_your_creativity/screen.png
├── sketch_detail/screen.png
├── profile/screen.png
├── settings/screen.png
└── daily_sketch/DESIGN.md
```

Use `timer_selection_fixed` rather than the earlier `timer_selection` variant.

The export establishes the intended overall tone well:

- warm paper-like background;
- muted sage primary action colour;
- large editorial headings;
- spacious layouts;
- soft rounded cards;
- thin line icons;
- artwork-led composition;
- minimal navigation chrome.

The following Stitch details must be corrected during implementation:

1. The three words are **one prompt**, not three selectable prompts. Replace copy such as “Tap a prompt” with wording that explains the user should use all three words.
2. Do not place a timer badge on an individual word card. The timer applies to the entire Sketch Session.
3. Feed cards must include version-one social actions: Like and Reflection.
4. The Review Submission screen remains in the flow and should support retaking/replacing the image and saving a Draft.
5. The Save Your Creativity screen remains and acts as the guest authentication checkpoint.
6. Submission Detail includes Likes and Reflections in version one.
7. Settings must not include “Canvas Default Setup”; the app has no digital canvas. Replace it with timer preference and relevant account/privacy controls.
8. Home uses the community feed below the prompt and reflects whether the current user has already submitted today.

---

## 3. Experience goals

### 3.1 Calm

The interface should lower the psychological cost of starting. Screens should not feel busy, urgent, or metric-heavy. Use whitespace, a restrained palette, short copy, and one obvious primary action per decision point.

### 3.2 Tactile

The visual language should evoke paper, card, sketchbooks, and high-quality stationery without using literal textures everywhere. Warm surfaces, soft tonal layering, and large rounded rectangles should create a physical-journal feeling.

### 3.3 Creative, not childish

The product should be welcoming to beginners without becoming playful in a juvenile way. Avoid cartoon mascots, confetti overload, bright rainbow accents, or overly cute copy.

### 3.4 Social, not performative

Likes and Reflections should be clear and useful but visually subordinate to the artwork. Do not use oversized counts, popularity labels, trending badges, or ranking indicators.

### 3.5 Native

Use standard iOS behaviours whenever they are a good fit:

- `NavigationStack`;
- sheets and full-screen covers;
- native camera/photo-picker controllers;
- system share sheet;
- system confirmation dialogs;
- Dynamic Type;
- SF Symbols;
- system haptics;
- standard keyboard and focus behaviour;
- system appearance support.

The app should not look like a webpage translated directly into SwiftUI.

---

## 4. Visual design system

## 4.1 Colour model

Use semantic colour tokens rather than hard-coded values throughout views.

The supplied Stitch palette is based on warm cream surfaces and muted sage actions. The following token set should be created in the iOS asset catalogue or a Swift design-system layer.

### Light appearance

| Token | Suggested value | Purpose |
|---|---:|---|
| `background` | `#FFF8F3` | Main app background |
| `surfacePrimary` | `#FFFFFF` | Highest-contrast cards and image frames |
| `surfaceSecondary` | `#FAF2EC` | Tonal cards and grouped settings |
| `surfaceTertiary` | `#F4ECE7` | Inputs, secondary controls, selected-neutral state |
| `surfaceElevated` | `#EEE7E1` | Sheets or layered controls where needed |
| `textPrimary` | `#1E1B18` | Main text |
| `textSecondary` | `#5F5E5B` | Supporting copy and metadata |
| `textTertiary` | `#76786F` | Placeholder and low-emphasis metadata |
| `primary` | `#585E4C` | Main action and selected state |
| `primaryPressed` | `#434937` | Pressed action state |
| `primarySoft` | `#DFE5CD` | Selected chip or low-emphasis sage background |
| `onPrimary` | `#FFFFFF` | Text/icons over primary |
| `divider` | `#E0D9D3` | Hairline separators |
| `outline` | `#C7C7BD` | Radio controls, field outlines when required |
| `danger` | `#BA1A1A` | Destructive actions and error emphasis |
| `dangerSoft` | `#FFDAD6` | Error container |
| `success` | `#5E6B52` | Success iconography where distinct from primary is needed |

### Dark appearance

Dark mode should remain warm and low-glare rather than using pure black.

| Token | Suggested value | Purpose |
|---|---:|---|
| `background` | `#1C1A18` | Main background |
| `surfacePrimary` | `#26231F` | Primary cards |
| `surfaceSecondary` | `#2E2A26` | Tonal groups |
| `surfaceTertiary` | `#37322D` | Inputs and secondary controls |
| `surfaceElevated` | `#403A34` | Sheets/elevated surfaces |
| `textPrimary` | `#F7EFE9` | Main text |
| `textSecondary` | `#CBC4BE` | Supporting text |
| `textTertiary` | `#A9A29C` | Placeholder and metadata |
| `primary` | `#C3C9B2` | Main action in dark mode |
| `primaryPressed` | `#AAB19B` | Pressed action |
| `primarySoft` | `#434937` | Soft selected state |
| `onPrimary` | `#181D0F` | Text/icons over dark-mode primary |
| `divider` | `#46413C` | Separators |
| `outline` | `#625D57` | Control outlines |
| `danger` | `#FFB4AB` | Destructive emphasis |
| `dangerSoft` | `#5D1F1B` | Error container |

These values are starting tokens. Minor adjustments are acceptable to achieve WCAG contrast and consistency with native materials, but the warm-paper and muted-sage character must remain.

### Colour usage rules

- Reserve `primary` for meaningful actions, selection, progress, and active navigation.
- Do not introduce multiple bright accent colours for different social actions.
- The Like heart may fill with `primary`, not bright red, to preserve the restrained palette. `danger` remains reserved for destructive or error states.
- Use tonal surfaces to create depth before using shadows.
- Artwork colours must not be altered to match the interface.
- Do not use a pure white full-screen background in light mode except for image framing when useful.

---

## 4.2 Typography

Use the native San Francisco typeface through SwiftUI system fonts. The Stitch export uses Inter as a web approximation; do not bundle Inter merely to match it.

Create semantic text styles rather than scattering point sizes.

| Style | SwiftUI starting point | Typical use |
|---|---|---|
| `display` | `.system(size: 38, weight: .bold, design: .default)` with Dynamic Type scaling | Major Home and marketing headings |
| `title1` | `.largeTitle.bold()` | Screen identity where space allows |
| `title2` | `.title.bold()` | Major section title |
| `title3` | `.title2.weight(.semibold)` | Sheet title and profile name |
| `headline` | `.headline` | Card title, primary metadata |
| `bodyLarge` | `.body` or 17 pt equivalent | Main supporting copy |
| `body` | `.body` | Standard labels and content |
| `bodySmall` | `.subheadline` | Secondary metadata |
| `caption` | `.caption` | Dates, counts, timing |
| `labelCaps` | `.caption.weight(.semibold)` with modest tracking | Section labels and prompt chips |
| `timer` | monospaced system font, approximately 72–104 pt depending on device | Active countdown |

Rules:

- Support Dynamic Type for all user-facing text.
- Use monospaced digits for the timer to prevent width movement.
- Avoid uppercasing long text. Uppercase is acceptable for short section labels such as `ACCOUNT` or prompt chips.
- Keep paragraph line length comfortable and use expanded line spacing on benefit-led onboarding copy.
- Use weight and spacing before using colour to create hierarchy.
- Never render essential metadata below an accessible contrast threshold.

---

## 4.3 Spacing

Base spacing scale:

```text
4, 8, 12, 16, 20, 24, 32, 40, 48, 64
```

Recommended semantic tokens:

- `screenHorizontal`: 24 pt on standard iPhones; may reduce to 20 pt on compact widths.
- `screenTop`: respect safe area plus 12–20 pt depending on navigation style.
- `sectionGap`: 40 pt.
- `contentGapLarge`: 32 pt.
- `contentGap`: 16 pt.
- `contentGapSmall`: 8 pt.
- `cardPadding`: 20–24 pt.
- `controlHeight`: minimum 52 pt; primary actions typically 56–64 pt.
- `minimumTouchTarget`: 44 × 44 pt.

Avoid dense lists. Settings may use grouped rows, but Home, Detail, and Profile should have generous vertical separation.

---

## 4.4 Shape

Create reusable radius tokens:

- `radiusSmall`: 8 pt;
- `radiusMedium`: 12 pt;
- `radiusLarge`: 18 pt;
- `radiusCard`: 24 pt;
- `radiusHero`: 28–32 pt;
- `radiusPill`: full capsule.

Use:

- 24–28 pt on artwork and prompt cards;
- 16–20 pt on grouped settings and text fields;
- capsule shape for compact chips and small metadata controls;
- full-width primary buttons with 18–24 pt radius or capsule treatment.

The shape language should feel soft and consistent. Do not mix sharp rectangular controls with heavily rounded cards without reason.

---

## 4.5 Elevation and materials

Depth should come primarily from tonal surfaces.

When a shadow is needed:

```text
colour: warm near-black
opacity: 0.04–0.08
blur: 16–24 pt
y offset: 6–10 pt
```

Use shadow sparingly on:

- the main image-review card;
- the Timer Selection sheet;
- the Save Your Creativity preview;
- floating controls over images.

Navigation bars and tab bars may use native material blur when content scrolls behind them. Avoid strong glassmorphism or high-opacity frosted cards throughout the interface.

---

## 4.6 Iconography

Use SF Symbols with a consistent thin or regular weight.

Suggested symbols:

- Home: `house`
- Profile: `person`
- Settings: `gearshape`
- New sketch: `square.and.pencil` or `pencil`
- Timer: `timer`
- Pause: `pause.fill`
- Resume: `play.fill`
- Finish: `checkmark`
- Cancel: `xmark`
- Camera: `camera`
- Photo library: `photo.on.rectangle`
- Retake/replace: `arrow.triangle.2.circlepath.camera`
- Like: `heart` / `heart.fill`
- Reflection: `bubble.left`
- Share: `square.and.arrow.up`
- More: `ellipsis`
- Streak: `flame` only if restrained; alternatively `sparkles` or calendar continuity symbol
- Reminder: `bell`
- Error: `exclamationmark.triangle`

Icons should be accompanied by text when meaning may not be obvious. Avoid custom glyphs unless the brand later has a deliberate icon set.

---

## 4.7 Haptics and sound

Use subtle system haptics:

- selection haptic when choosing a timer;
- light impact when Start begins;
- success haptic when countdown reaches zero;
- success haptic after publication;
- soft notification haptic when Like toggles;
- warning haptic before destructive confirmation only when appropriate.

Sound is optional and off by default. Do not play an intrusive alarm at timer completion. A gentle system-compatible tone may accompany the completion haptic if enabled later.

Respect reduced-motion and system haptic preferences.

---

## 5. Navigation architecture

## 5.1 Primary tabs

Authenticated and guest users both have access to:

- **Home**
- **Profile**

Settings is reached from the profile toolbar rather than requiring a third permanent tab, matching the Stitch profile concept. This keeps the tab bar simple and gives artwork more room.

Guest Profile behaviour:

- show a lightweight benefit screen and sign-in/create-account options;
- do not present a fake empty personal profile.

Recommended tab bar:

- native bottom tab bar;
- Home and Profile icons;
- labels visible for both for accessibility, even if the final visual treatment reduces emphasis on the inactive label;
- selected state uses `primary`;
- background uses native material or the warm app background with a divider.

A three-tab structure with explicit Settings is acceptable only if later usability testing demonstrates that profile toolbar access is insufficient. The initial implementation should follow the two-tab Stitch model.

## 5.2 Navigation stacks

Each tab owns its own `NavigationStack` so users can move between tabs without losing depth.

Home stack destinations:

- Submission Detail;
- another user’s Profile;
- Reflections where presented separately;
- report flow.

Profile stack destinations:

- Submission Detail;
- Edit Profile;
- Settings;
- blocked users;
- legal/support pages.

## 5.3 Modal presentation

Use a bottom sheet for:

- Timer Selection;
- quick report reason selection;
- compact social actions where suitable.

Use a full-screen cover for:

- Active Sketch Session;
- camera capture;
- Review Submission when preserving a focused flow;
- Save Your Creativity if authentication is embedded in a focused conversion flow.

Use system sheets/controllers for:

- photo picker;
- share sheet;
- confirmation dialogs;
- Descope provider UI where required.

## 5.4 Deep links and restoration

The navigation system should support opening:

- Home from daily reminder;
- a Submission Detail from a shared link when public links exist;
- a preserved Review Submission after authentication;
- an active Sketch Session after app restoration;
- a local Draft from Home/Profile.

---

## 6. Reusable component catalogue

## 6.1 AppHeader

A minimal navigation header with:

- optional back button;
- centred or leading title according to context;
- optional trailing action;
- warm translucent background when content scrolls underneath.

Do not add a large header to the Active Sketch screen.

## 6.2 PrimaryButton

Properties:

- full width within screen margins;
- 56–64 pt height;
- `primary` fill;
- `onPrimary` text and icon;
- semibold label;
- rounded rectangle or capsule;
- loading state with progress indicator and stable width;
- disabled state with reduced contrast but still legible;
- pressed state using `primaryPressed` and slight scale or opacity change.

## 6.3 SecondaryButton

- tonal `surfaceTertiary` fill;
- `textPrimary` or `primary` label;
- no strong border;
- same height and shape family as PrimaryButton when paired.

## 6.4 TertiaryTextButton

For actions such as **Save to Drafts**, **Sign In**, **Continue Later**, or **Change timer**.

- text-only or low-emphasis background;
- minimum touch target maintained;
- never use low-contrast grey for an important recovery action.

## 6.5 PromptWordCard

A non-selectable display card for one of the three words.

Contents:

- optional restrained category-like symbol for visual interest;
- word in large semibold type;
- no independent timer badge;
- no radio or disclosure indicator;
- no individual tap state.

All three cards belong inside one accessibility group whose label is similar to:

> Today’s prompt: Chocolate, Coffee, Banana.

## 6.6 PromptGroup

A container that makes the three cards read as one challenge.

Preferred initial layout on standard iPhones:

- one full-width card above two equal half-width cards, matching the strongest Stitch Home concept;
- the asymmetry is visual only, not semantic;
- rotate which word appears first only if the prompt order is intentionally variable; otherwise preserve the stored order.

Alternative on compact widths or large Dynamic Type:

- three full-width stacked cards.

Do not use the fanned-card layout as the default if it obscures any word. It may be used as a decorative onboarding illustration, not as the primary accessible prompt presentation.

## 6.7 SubmissionCard

The central feed component.

Composition:

1. owner row;
2. artwork image;
3. prompt/timer/date metadata;
4. optional caption preview;
5. social action row.

The Stitch Home places user metadata beneath the image. Either above or below is acceptable, but one approach must be used consistently. Recommended:

- compact owner row above the image for clearer tap target;
- artwork immediately below;
- prompt and timing below artwork;
- social row last.

Social row:

- heart icon and count;
- Reflection icon and count;
- Share action optional on feed, required on detail;
- buttons have at least 44 pt touch targets;
- counts use `caption` or `bodySmall`.

Artwork:

- full available width;
- aspect ratio based on derivative metadata;
- maximum reasonable height so one very tall image does not dominate indefinitely;
- `radiusCard` clipping;
- neutral placeholder while loading;
- no crop that removes important parts by default; prefer fit inside a tonal frame when aspect ratio is unusual.

## 6.8 Avatar

Sizes:

- 28–32 pt in feed rows;
- 44–52 pt in Submission Detail;
- 72–96 pt on Profile;
- initials or neutral system symbol fallback.

## 6.9 PromptChip

Compact capsule showing one word in Submission Detail or profile metadata.

- `surfaceTertiary` background;
- uppercase or semibold small text with moderate tracking;
- all three chips shown together;
- wraps to multiple lines under large Dynamic Type.

## 6.10 SocialActionButton

Reusable Like, Reflection, and Share control.

States:

- inactive;
- active Like;
- loading/optimistic pending;
- disabled for unavailable content;
- guest tap that initiates authentication.

The entire icon-plus-count region is tappable.

## 6.11 ReflectionRow

Shows:

- avatar;
- username;
- Reflection body;
- relative or absolute time;
- owner menu for deletion;
- report action for other users.

Use a soft tonal bubble only if it does not make the thread visually heavy. The Stitch detail bubble is a useful reference.

## 6.12 EmptyState

Contains:

- restrained SF Symbol or simple illustration;
- short title;
- one sentence of explanation;
- optional single action.

Avoid celebratory or guilt-inducing language.

## 6.13 ErrorState

Contains:

- clear user-safe message;
- retry or alternative action;
- optional technical reference only when useful to support;
- does not expose server internals.

## 6.14 Skeletons and image placeholders

Use simple tonal blocks matching final shapes. Avoid shimmering animation when Reduce Motion is enabled. The prompt can appear before feed skeletons resolve.

---

## 7. Screen specifications

## 7.1 Home — guest, no active work

### Purpose

Introduce today’s challenge and the community in one screen.

### Reference

Use `home_today_s_inspiration/screen.png` as the primary visual reference, with the corrected prompt semantics and added social actions.

### Layout

From top to bottom:

1. compact app header:
   - leading new-sketch/pencil icon is optional because Start Sketch already exists;
   - centred **Daily Sketch** wordmark/title;
   - no unnecessary trailing action;
2. large **Today’s Inspiration** heading;
3. supporting line:
   - preferred: **Use all three words as inspiration for today’s sketch.**
4. PromptGroup with all three words;
5. full-width **Start Sketch** button;
6. section title **Community Sketches** or **Recent Sketches**;
7. reverse-chronological SubmissionCard list;
8. bottom tab bar.

Do not use **Tap a prompt to start your daily practice** because the cards are not individually selectable.

### Behaviour

- pull to refresh feed and prompt status;
- infinite scroll near the end;
- tapping Start Sketch presents Timer Selection;
- tapping owner opens Profile;
- tapping artwork opens Submission Detail;
- guest social action invokes authentication and returns to the intended action.

### Empty feed

Keep the prompt and Start Sketch usable. Below, show:

**No sketches yet**
**Be the first to share an interpretation of today’s prompt.**

Primary feed-empty action is unnecessary because Start Sketch already appears above.

---

## 7.2 Home — authenticated, not yet submitted today

Same composition as guest Home.

Additional behaviour:

- recover server-backed timer preference;
- show an active-session banner if a session exists;
- show a Draft card if an unpublished local Draft exists;
- social controls operate immediately.

Active session banner example:

**You have a sketch in progress**
`Resume` and a subtle `Discard` option.

Draft card example:

**Ready when you are**
Preview thumbnail, prompt date, and `Continue`.

These recovery cards appear between the PromptGroup and community section, but must not overwhelm Start Sketch.

---

## 7.3 Home — submitted today

Replace the single Start Sketch call-to-action area with a compact completion state while keeping the prompt visible.

Recommended composition:

- small checkmark-in-circle or subtle sage indicator;
- **You sketched today**;
- secondary metadata such as **5 minute sketch** only when referring to the most recent Submission;
- PrimaryButton: **Create Another Sketch**;
- Secondary/Tertiary action: **View My Sketch** or **View My Sketches**.

Do not hide the prompt after completion. The user may want to create another interpretation.

Avoid confetti. A small success transition immediately after publication is enough.

---

## 7.4 Timer Selection sheet

### Reference

`timer_selection_fixed/screen.png`.

### Presentation

- bottom sheet with a visible grabber;
- medium or large detent depending on content size and Dynamic Type;
- warm elevated background;
- background content dimmed and blurred by the system.

### Content

- title: **How long would you like to sketch?**
- selectable rows:
  - 1 minute;
  - 3 minutes;
  - 5 minutes;
  - 10 minutes;
  - No timer;
- native-style radio indicator or checkmark;
- divider;
- **Remember this choice** checkbox/toggle row;
- PrimaryButton: **Start**, with timer symbol.

### Selection behaviour

- no option selected initially unless product chooses a sensible first-use default;
- Start disabled until an option is selected;
- row is fully tappable, not only the radio circle;
- selection haptic;
- Remember this choice defaults off;
- sheet dismiss gesture should not create a session.

### Remembered choice bypass

When a choice is remembered, Start Sketch begins directly. Show a small temporary banner or Active Session control that makes **Change next time** discoverable, but do not interrupt the current start with another confirmation.

---

## 7.5 Active Sketch — countdown

### Reference

`sketch_session/screen.png`.

### Presentation

A focused full-screen experience with no tab bar.

### Layout

- large central whitespace;
- subtle pencil symbol;
- state label: **SKETCHING…**;
- monospaced countdown, e.g. `04:59`;
- full-width primary Pause/Resume control;
- two secondary controls side by side:
  - Finish;
  - Cancel.

The three prompt words should remain accessible without cluttering the screen. Recommended options:

- a compact prompt-chip row near the top; or
- a **View prompt** disclosure that expands briefly.

Do not omit the prompt entirely because the user may need to refer back to it.

### Timer behaviour

- timer remains accurate across backgrounding;
- paused state changes primary control to **Resume**;
- completion changes the central state to **Time’s up — keep going or capture your sketch**;
- actions after completion:
  - **Take Photo** primary;
  - **Keep Sketching** secondary;
- Finish before zero proceeds to capture choice without negative wording.

### Cancel

Present confirmation:

**End this sketch session?**
**Your drawing will not be deleted, but this timer session will be marked as abandoned.**

Actions: **Keep Sketching**, **End Session**.

---

## 7.6 Active Sketch — No timer

Use the same visual structure but replace the large countdown with:

- **Sketching…**;
- optional elapsed wall-clock time in smaller text, or no duration at all.

Primary action: **Finish**.
Secondary action: **Cancel**.

Do not label elapsed wall-clock time as exact drawing time.

---

## 7.7 Capture source choice

After Finish, present a native action sheet or simple focused screen:

**Add your sketch**

- **Take Photo**;
- **Choose from Library**;
- **Go Back**.

If camera access is unavailable, make Choose from Library the clear alternative.

Use native permission prompts only at the moment the capability is needed, preceded by concise contextual copy if helpful.

---

## 7.8 Review Submission

### Reference

`confirm_submission/screen.png`.

### Presentation

Full-screen flow with a simple navigation header and back action.

### Layout

1. title **Ready to share?**;
2. supporting copy **Review your sketch before sharing it with the community.**;
3. large image-preview card;
4. overlay or row containing Prompt Date, all three words, and replace/retake action;
5. timer metadata;
6. **Optional caption** label;
7. borderless tonal multiline text field;
8. PrimaryButton **Submit to Community**;
9. Tertiary action **Save to Drafts**.

The Stitch preview overlay says only **Daily Prompt**; replace it with meaningful prompt information or a concise expandable treatment.

### Image review

The preview should:

- preserve aspect ratio;
- allow tap-to-view larger if needed;
- clearly expose **Retake** or **Replace**;
- show processing/upload states without hiding the image.

### Keyboard behaviour

- content scrolls above keyboard;
- Submit remains reachable;
- caption text is preserved if the user replaces the photo or authenticates;
- character count appears near the limit, not permanently if it adds clutter.

### Save to Drafts

- saves locally;
- provides a quiet success message;
- returns to Home or Profile based on flow;
- Home shows a recoverable Draft card.

---

## 7.9 Save Your Creativity

### Reference

`save_your_creativity/screen.png`.

### Purpose

Convert a guest only after they have created something, while reassuring them that their work is safe.

### Layout

- generous top whitespace;
- rounded thumbnail preview of the current sketch;
- title **Save Your Creativity**;
- copy:
  - **Create a free account to save your sketches, build your history, and share with the community.**
- PrimaryButton **Create Free Account**;
- SecondaryButton or text action **Sign In**;
- SecondaryButton **Continue Later**;
- optional small brand line **YOUR DIGITAL SANCTUARY AWAITS.** only if it tests well; it is decorative and may be removed for clarity.

### Behaviour

- Create Free Account enters Descope sign-up;
- Sign In enters Descope sign-in;
- Continue Later preserves a local Draft and returns to Home;
- backing out also preserves the current review state unless the user explicitly discards it;
- after authentication, return to Review Submission with image and caption intact.

Do not upload publicly before authentication succeeds.

---

## 7.10 Authentication and onboarding

The Stitch archive does not include full authentication screens, so use native, restrained screens consistent with the rest of the product.

### Authentication entry

Content:

- Daily Sketch title/mark;
- concise value statement;
- Descope-supported sign-in actions;
- privacy/terms links;
- dismiss or Continue Later where the flow permits.

Do not create a long carousel onboarding sequence.

### Profile completion

After first authentication, request only required public information:

- username;
- display name;
- optional avatar;
- optional daily reminder choice.

If authentication occurred from Review Submission, the user should reach publication quickly. Defer optional bio and appearance settings.

### Username field

- live validation with debounce;
- clear case-insensitive availability state;
- suggestions if unavailable;
- no public display of email by default.

---

## 7.11 Submission Detail

### Reference

`sketch_detail/screen.png`.

### Navigation header

- back button;
- title may be **Sketch** or a short caption excerpt;
- do not require a formal title field;
- trailing overflow menu.

### Layout

1. large artwork card;
2. owner row with avatar, display name, username;
3. three PromptChips;
4. timer and Prompt Date metadata;
5. caption, when present;
6. divider;
7. social action row:
   - Like and count;
   - Reflections and count;
   - Share;
8. **Reflections** heading;
9. Reflection list;
10. composer pinned above the keyboard or placed at the end of the thread.

### Like

- `heart` to `heart.fill` animation;
- fill uses sage primary;
- optimistic count update;
- rollback with unobtrusive error if request fails;
- guest tap opens authentication and returns to the detail.

### Reflections

The Stitch copy **Add a reflection…** should be retained.

Composer:

- current user avatar;
- single-line field that expands to a reasonable maximum;
- **Post** enabled only with non-whitespace content;
- guest tap invokes authentication while preserving text.

Reflection row:

- username;
- body;
- timestamp;
- own delete menu;
- report menu for others.

### Overflow menu

Own Submission:

- Share;
- Delete Submission.

Another user’s Submission:

- Share;
- Report;
- Block User.

Delete requires destructive confirmation.

---

## 7.12 Public Profile

### Reference

`profile/screen.png`.

### Header

- back button when opened from another screen;
- settings gear only on own profile;
- centred avatar;
- display name;
- username;
- optional bio;
- statistics:
  - Submission count;
  - current day streak;
- Edit Profile only on own profile.

Use **12 day streak** or **12-day streak** rather than ambiguous symbols alone. A small restrained icon may accompany it.

### Gallery

The Stitch single-column journal layout is the preferred starting point because it lets artwork breathe.

Each entry contains:

- image;
- optional caption or prompt-derived label;
- Prompt Date;
- optional compact Like/Reflection counts on own or public profile if they do not clutter.

On wider devices, an adaptive two-column layout is acceptable. On standard iPhones, use one large column or a two-column masonry layout only if image variety remains legible. Do not use tiny square crops that erase the sketchbook quality.

### New Submission card

On own profile, end the current loaded content with a dashed or tonal **New Submission** card only when it does not duplicate a persistent action awkwardly. It may be omitted if the bottom tab and Home already make creation obvious.

### Empty profile

Own profile:

**Your sketchbook starts here**
**Create your first response to today’s prompt.**
Button: **Start Sketch**.

Another profile:

**No sketches shared yet.**

---

## 7.13 Edit Profile

Fields:

- avatar with Change Photo;
- display name;
- username;
- optional bio;
- Save.

Behaviour:

- validate username;
- show unsaved-change confirmation on dismiss;
- image upload progress if avatar changes;
- no email editing unless Descope flow explicitly supports it;
- no follower or social-link fields in version one.

---

## 7.14 Guest Profile tab

Show a calm benefit screen rather than an error.

Suggested content:

- sketchbook/avatar illustration;
- **Keep your creative history**;
- explanation that an account saves Submissions, streaks, Likes, and Reflections;
- **Create Free Account**;
- **Sign In**;
- no forced modal on simply opening the tab.

If a local Draft exists, show its thumbnail and explain that it will remain available after sign-in.

---

## 7.15 Settings

### Reference

`settings/screen.png`, corrected for product scope.

### Structure

Use a native grouped settings list with warm tonal containers and section labels.

#### Account

- avatar, display name, username;
- Edit Profile;
- email or authentication-method summary where appropriate;
- Timezone.

#### Notifications

- Daily Reminder toggle;
- Reminder Time;
- system-permission state and shortcut to iOS Settings if denied.

#### Sketch Preferences

- Remember Timer Choice toggle;
- Default Timer row showing 1, 3, 5, 10 minutes, or No timer;
- Default Timer disabled when remembering is off, or opening it enables remembering after confirmation.

#### Appearance

- System;
- Light;
- Dark.

#### Safety and privacy

- Blocked Users;
- Community Guidelines;
- Privacy;
- Terms.

#### Support

- Help & Support;
- About Daily Sketch;
- app version.

#### Account actions

- Sign Out;
- Delete Account.

Use red only for destructive actions. Delete Account must not sit immediately beside a casual action without separation.

Remove **Canvas Default Setup** from the Stitch design.

---

## 7.16 Likes and Reflections in the feed

The Stitch Home feed lacks social controls. Version one must add them without making cards feel like Instagram clones.

Recommended social row below metadata:

```text
[heart] 24      [bubble] 3
```

- no **View all comments** engagement copy;
- no repeated Share button in feed unless testing shows it is valuable;
- no follower count;
- no ranking badge;
- subtle divider or spacing between cards, not boxed social chrome.

A compact caption preview may appear above the social row, limited to two or three lines with a **more** expansion.

---

## 7.17 Report flow

Present a native sheet:

- title **Report this sketch** / **Report this reflection** / **Report this profile**;
- list of reasons;
- optional detail field after selecting Other;
- submit confirmation;
- explanatory copy that reports are private.

After successful report:

- dismiss sheet;
- show a small confirmation banner;
- offer **Block User** where relevant.

---

## 7.18 Blocked users

Settings destination listing blocked users with:

- avatar;
- display name;
- username;
- **Unblock** action.

Empty state:

**No blocked users.**

---

## 7.19 Account deletion

Use a dedicated screen or multi-step confirmation, not only a one-line alert.

Explain:

- public profile will disappear;
- Submissions and images will be removed according to policy;
- Likes and Reflections may be deleted or anonymised as specified technically;
- action may not be immediately reversible.

Require explicit final confirmation. Do not use dark patterns.

---

## 8. State specifications

## 8.1 Loading

### Prompt

- show heading and word-card skeletons;
- do not block navigation to Profile/Settings;
- if cached prompt is valid, show it immediately with a small refresh state.

### Feed

- show two or three artwork-card skeletons;
- load independently of prompt;
- use pagination footer spinner rather than replacing loaded content.

### Detail/Profile

- use stable skeleton geometry to prevent layout jumping;
- load lower-priority social counts after core artwork if necessary.

## 8.2 Empty

Empty states must preserve the screen’s purpose and avoid shame.

Examples:

- Feed: **No sketches yet. Be the first to interpret today’s prompt.**
- Reflections: **No reflections yet. Share a kind thought.**
- Own Profile: **Your sketchbook starts here.**
- Other Profile: **No sketches shared yet.**
- Drafts: **No drafts waiting.**
- Blocked users: **No blocked users.**

## 8.3 Errors

Use inline errors near the affected action when possible.

Examples:

- Feed failure: preserve prompt, show **Couldn’t load community sketches** and Retry.
- Like failure: roll back and show a brief banner.
- Reflection failure: preserve text and show Retry.
- Upload failure: preserve image and caption; show Retry and Save to Drafts.
- Session sync failure: continue timer locally and mark sync pending.
- Authentication failure: keep current Draft and allow retry or Continue Later.

## 8.4 Offline

- cached Home prompt and feed may be displayed with an offline indicator;
- Start Sketch still works;
- local timer works;
- photo review works;
- publication waits or saves to Draft;
- social actions should clearly indicate they require reconnection.

Do not show repeated modal alerts for every unavailable action.

## 8.5 Success

Use small, restrained success feedback:

- timer completion haptic and state change;
- upload completion progress resolving to checkmark;
- publication success banner or subtle transition;
- report submitted banner;
- profile saved confirmation.

Avoid full-screen confetti or achievement modals.

---

## 9. Motion specification

Motion should make state changes understandable, not decorate every interaction.

Recommended transitions:

- Timer Selection sheet uses native spring presentation.
- Selected timer radio animates with a short scale/fade.
- Start transitions into Active Sketch with a gentle fade/scale rather than a dramatic zoom.
- Countdown digits update without bouncing.
- Pause changes to Resume with a crossfade.
- Like fills with a 150–220 ms scale and opacity transition.
- New Submission inserted into Home using a soft move/fade.
- Image upload progress transitions to success checkmark.
- Navigation uses standard iOS push and sheet transitions.

When Reduce Motion is enabled:

- remove scale and parallax;
- prefer opacity transitions;
- disable shimmer;
- do not animate fanned prompt cards.

No background animation is required on the timer screen. If a subtle radial glow is used, it must be almost imperceptible and disabled under Reduce Motion.

---

## 10. Accessibility specification

### 10.1 VoiceOver

- group the three prompt cards as one prompt while still allowing individual word reading;
- announce timer choice and Remember this choice state;
- countdown should not announce every second automatically;
- provide manual accessibility value for remaining time;
- label Like state as **Like, not selected** or **Unlike, selected**;
- include counts in accessible labels;
- artwork images use a generic description derived from caption/prompt until optional alt text exists;
- icon-only overflow and share buttons require labels.

### 10.2 Dynamic Type

- layouts must support at least accessibility text sizes;
- PromptGroup changes from 1+2 grid to vertical stack;
- social actions may wrap;
- prompt chips wrap;
- settings rows grow vertically;
- fixed-height text fields must become minimum-height fields;
- timer controls remain reachable without clipping.

### 10.3 Contrast

- verify all semantic colour combinations;
- inactive icons cannot rely on extremely light grey;
- placeholder text must remain distinguishable;
- error text and controls meet contrast requirements;
- artwork overlays require a solid or material background behind text.

### 10.4 Touch and motor access

- all controls at least 44 × 44 pt;
- full settings and timer rows tappable;
- no swipe-only essential actions;
- destructive actions available through menus and confirmation screens;
- avoid tiny inline links for primary recovery paths.

### 10.5 Cognitive accessibility

- one primary decision per screen;
- consistent terminology;
- clear progress and recovery;
- no punitive streak language;
- no surprise publication;
- no timer pressure in No timer mode.

---

## 11. Responsive behaviour

The first target is portrait iPhone, but layouts must adapt to:

- compact iPhone widths;
- large iPhone widths;
- landscape where supported;
- iPad running the iPhone app or future native layout;
- Dynamic Type.

### Home

- maintain 20–24 pt margins;
- PromptGroup stacks under compact width or large text;
- feed artwork never exceeds readable content width on iPad; centre in a max-width column.

### Active Sketch

- central timer scales to fit width;
- controls move to vertical stack if side-by-side buttons become too narrow;
- safe areas respected.

### Review Submission

- content scrolls;
- image preview uses available width with maximum height;
- primary action remains visible or easily reachable.

### Profile

- use a max-width journal column on iPad;
- optionally use two columns for artwork when images remain large enough;
- header remains centred.

---

## 12. Design-system implementation guidance

Create a `DesignSystem` module or folder containing:

```text
DesignSystem/
├── AppColors.swift
├── AppTypography.swift
├── AppSpacing.swift
├── AppRadii.swift
├── AppShadows.swift
├── Components/
│   ├── PrimaryButton.swift
│   ├── SecondaryButton.swift
│   ├── PromptGroup.swift
│   ├── PromptWordCard.swift
│   ├── SubmissionCard.swift
│   ├── AvatarView.swift
│   ├── PromptChip.swift
│   ├── SocialActionButton.swift
│   ├── ReflectionRow.swift
│   ├── EmptyStateView.swift
│   ├── ErrorStateView.swift
│   └── LoadingSkeleton.swift
└── Previews/
```

Requirements:

- components consume semantic tokens;
- no feature view hard-codes hex colours;
- preview each component in Light and Dark mode;
- preview normal, loading, disabled, selected, error, and large-text states;
- use sample artwork fixtures safe to commit;
- avoid building a generic UI framework larger than the product needs.

---

## 13. Copy and tone

The voice is calm, direct, encouraging, and non-judgemental.

Prefer:

- **Today’s Inspiration**
- **Use all three words as inspiration for today’s sketch.**
- **Start Sketch**
- **How long would you like to sketch?**
- **No timer**
- **Remember this choice**
- **Ready to share?**
- **Add a thought about your creative process…**
- **Submit to Community**
- **Save to Drafts**
- **Save Your Creativity**
- **Add a reflection…**
- **You sketched today**
- **Create Another Sketch**

Avoid:

- **Crush today’s challenge**
- **You failed your streak**
- **Trending masterpiece**
- **Beat other artists**
- **Engagement** as user-facing language
- **Content** when **sketch** or **work** is clearer
- **Tap a prompt** because the three words are not separately selectable

Error copy should say what happened and what the user can do next.

---

## 14. Design acceptance checklist

The design implementation is ready for version-one release when all of the following are true:

### Home

- all three words read as one challenge;
- Start Sketch is the only initial creation action;
- the community feed appears underneath;
- feed cards include Likes and Reflections;
- artwork dominates card composition;
- completed-today state supports View and Create Another;
- active session and Draft recovery are represented.

### Timer and session

- preferred Timer Selection matches the fixed Stitch sheet;
- Remember this choice defaults off;
- No timer is available;
- Active Sketch is calm and focused;
- prompt remains accessible;
- backgrounding and restoration have understandable UI;
- Finish and Cancel are distinct and accessible.

### Capture and review

- camera and library are supported;
- photo can be retaken or replaced;
- Review Submission is mandatory before public sharing;
- caption is optional;
- upload progress and retry are visible;
- Draft saving preserves work.

### Guest conversion

- guest can reach Review Submission;
- Save Your Creativity shows the actual work;
- Create Account, Sign In, and Continue Later are present;
- authentication returns to the preserved review flow.

### Social

- Submission Detail includes Like, Reflections, and Share;
- Like state is clear;
- Reflection composer preserves text on failure/authentication;
- owner and moderation menus are available;
- no ranking or competitive treatment is introduced.

### Profile and settings

- profile shows avatar, identity, Submission count, streak, and artwork journal;
- own and other profiles differ appropriately;
- Settings includes reminder, timer preference, appearance, safety, support, and account controls;
- Canvas Default Setup is absent;
- Delete Account is deliberately presented.

### Quality

- Light and Dark mode are implemented;
- Dynamic Type layouts work;
- VoiceOver labels are complete;
- Reduce Motion is respected;
- loading, empty, error, success, offline, and permission states exist;
- reusable components use semantic tokens;
- physical-device review confirms controls and camera flow.

---

## 15. Canonical design decisions

- Use the Stitch warm-paper and muted-sage aesthetic.
- Use native SF typography rather than bundling Inter.
- Use two main tabs: Home and Profile; Settings is reached from Profile.
- Use the separated three-card PromptGroup as the accessible default, not individually selectable cards.
- Do not display an individual timer badge on a word card.
- Use a bottom sheet for Timer Selection.
- Use a focused full-screen Active Sketch experience.
- Keep Review Submission and Save Your Creativity as separate, valuable screens.
- Add Likes and Reflections to version-one feed/detail designs.
- Use Reflections as the user-facing term for comments.
- Use a large, journal-like Profile gallery rather than tiny square thumbnails.
- Remove Canvas Default Setup from Settings.
- Use restrained haptics and motion; no excessive celebration or gamification.
- Use native iOS share, camera, photo-picker, permission, and accessibility behaviours.
