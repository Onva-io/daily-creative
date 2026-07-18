# Daily Sketch — Product Specification

**Version:** 1.1
**Status:** Canonical baseline for implementation
**Product:** Daily Sketch
**Primary platform:** Native iOS application

## 1. Purpose of this document

This document defines what Daily Sketch is, who it is for, how it should behave, and what is included in the first production release.

It is the authoritative source for product scope and product behaviour. The other specification files have narrower responsibilities:

- `design.md` defines the visual language, screen composition, navigation presentation, component states, and interaction details.
- `architecture.md` defines the technical design, data model, API surface, security boundaries, and client/server responsibilities.
- `implementation.md` defines the phased delivery plan, acceptance gates, and engineering workflow.
- `infrastructure.md` defines local environments, deployment, CI/CD, storage, secrets, monitoring, and production operations.

Where a Stitch mock-up conflicts with this document, this document controls product behaviour and `design.md` controls the intended visual treatment. In particular, the daily challenge is always formed from **all three words together**. Individual word cards are not separate selectable prompts.

---

## 2. Product summary

Daily Sketch helps people introduce a small, achievable amount of creativity into every day.

Each calendar day, every user receives the same three-word inspiration prompt. A user can begin a sketch session, optionally choose a time limit, draw away from the phone, photograph the result, review it, and publish it to the community.

The social experience is built around shared interpretation rather than status. Users see how other people responded to the same constraint, can like sketches, leave short comments called **Reflections**, browse profiles, and build a personal archive of their own work.

Daily Sketch is not a digital drawing application. It does not provide a canvas, brushes, layers, or editing tools. The creative activity normally happens on paper or another physical medium. The app supplies:

- the inspiration;
- the time-box, when desired;
- the record of the session;
- the photo and publishing flow;
- the personal history;
- the community around the shared prompt.

---

## 3. Problem and opportunity

Many people want to be more creative but struggle with one or more of the following:

- an empty page feels too open-ended;
- creative work appears to require a large block of time;
- perfectionism makes starting difficult;
- there is no reliable cue to create;
- they do not have a lightweight way to record progress;
- conventional social platforms make sharing feel performative or competitive.

Daily Sketch reduces these barriers by supplying a small daily constraint and a clear path from intention to completion.

The core promise is:

> Open the app, receive three words, spend a few minutes making something, and keep a visible record of having created.

The shared prompt also produces a naturally interesting community. The value of the feed is not simply that it contains drawings; it contains many different interpretations of the same three words.

---

## 4. Product vision

Daily Sketch should become a calm daily ritual: part prompt book, part sketch journal, and part supportive creative community.

The app should make it realistic for a user to create something even on a busy day. A one-minute sketch is valid. A ten-minute sketch is valid. A longer untimed piece is valid. Several sketches in one day are valid. Missing a day is not treated as failure.

The product should feel more like opening a high-quality sketchbook than opening a high-pressure social network.

---

## 5. Product principles

### 5.1 Creativity before competition

Likes and comments exist to provide encouragement and conversation, not to establish rankings. There are no leaderboards, public popularity scores, or competitive streak comparisons in version one.

### 5.2 Starting must be easy

A returning user should be able to begin a session within seconds. The Home screen has one primary creation action. Timer selection appears after that action and can be skipped automatically when the user has chosen to remember a preference.

### 5.3 The three words are one shared prompt

Every published daily prompt contains exactly three ordered words. Users respond to the combination. The interface may visually separate the words, but it must not imply that the user chooses only one word.

### 5.4 Flexible participation

The timer supports the habit but does not police it. Users may choose a countdown or no timer, finish early, continue after a countdown ends, submit more than once, or save a captured image for later.

### 5.5 Artwork is the centre of the social experience

Feed and detail screens should give the sketch most of the available visual attention. Usernames, counts, timestamps, and controls remain clear but secondary.

### 5.6 Public sharing requires deliberate confirmation

Taking a photo does not immediately publish it. The user receives a dedicated review step where they can assess the image, retake or replace it, add an optional caption, and choose to publish or continue later.

### 5.7 Guest exploration is allowed; durable participation requires an account

A user may browse public content and begin the creative flow without signing in. An account is required to publish, maintain a history, like, comment, or manage a profile. Authentication must preserve the guest’s work in progress rather than forcing them to repeat the sketch or photo flow.

### 5.8 Native iOS behaviour

Daily Sketch should use familiar iOS patterns for navigation, sheets, camera permissions, photo selection, notifications, sharing, accessibility, and system appearance.

### 5.9 Product analytics must be honest

The app may measure elapsed wall-clock time between session events. It must not represent that duration as exact active drawing time, because the user may pause, become distracted, leave the app, or take the photo later.

---

## 6. Target users

### 6.1 Primary user

A person who wants to add a small amount of creativity to everyday life but benefits from a prompt and a simple structure.

This person may:

- enjoy drawing but not identify as an artist;
- have limited free time;
- struggle with open-ended choices;
- respond well to short time-boxes;
- want a private archive that can also be shared;
- enjoy seeing other people’s interpretations;
- dislike highly performative social media.

### 6.2 Secondary users

- experienced artists looking for a warm-up exercise;
- illustrators, designers, and students building consistency;
- friends or communities completing a shared daily challenge;
- journalers who want to add visual prompts to their practice;
- users who prefer physical media but still want a digital history.

### 6.3 Non-target use cases for version one

Daily Sketch is not intended to be:

- a professional portfolio-hosting platform;
- a full digital illustration suite;
- an art marketplace;
- a private messaging network;
- a competitive drawing game;
- a classroom-management system;
- an AI image-generation tool.

---

## 7. Product terminology

The following terms are canonical and should be used consistently in the product, code, API contract, and documentation.

### Daily Prompt

The shared set of exactly three words assigned to one product date.

### Prompt Date

The calendar date to which a Daily Prompt belongs. The technical specification defines the global date boundary. Every user sees the same active prompt at the same time.

### Sketch Session

The tracked period beginning when a user confirms a timer option or starts their remembered option. A Sketch Session may be completed, abandoned, or remain without a published Submission.

### Timer Option

One of the supported countdown durations or **No timer**.

### Submission

A published sketch image linked to a user, a Daily Prompt, and normally a Sketch Session. A user may publish multiple Submissions for the same Prompt Date.

### Draft

A captured or selected image and associated metadata that has not yet been published. Version one guarantees recoverable local drafts; synchronised cross-device drafts are not required.

### Reflection

The user-facing name for a comment on a Submission. In technical APIs and database objects, the resource may be named `comment`, but the iOS interface should normally say **Reflection** or **Reflections**.

### Like

A lightweight positive reaction represented by a heart. An authenticated user can like or unlike a public Submission.

### Streak

The number of consecutive Prompt Dates, ending today or yesterday, for which a user has at least one published Submission. Multiple Submissions on one date count once.

---

## 8. Version-one product scope

Version one is a complete social product, not only a private habit prototype.

### 8.1 Included in version one

- native iOS application;
- guest browsing;
- guest access to the prompt, timer, sketch session, camera, and review flow;
- Descope-backed account creation and sign-in;
- public user profiles;
- editable display name, username, avatar, and optional bio;
- one shared three-word Daily Prompt per Prompt Date;
- optional countdown timers of 1, 3, 5, and 10 minutes;
- No timer mode;
- remembered timer preference, off by default;
- recoverable Sketch Sessions;
- camera capture and photo-library selection;
- image review before publication;
- optional caption;
- recoverable local drafts;
- multiple Submissions per user per Prompt Date;
- reverse-chronological community feed;
- Submission detail screen;
- likes and like counts;
- Reflections and Reflection counts;
- deletion of the user’s own Reflections;
- deletion of the user’s own Submissions;
- public profile gallery and Submission history;
- personal streak display;
- configurable daily reminder;
- native iOS share sheet for a published Submission;
- reporting and basic blocking/moderation safeguards;
- account deletion;
- product analytics for the core funnel and Sketch Session timings.

### 8.2 Explicitly out of scope for version one

- following or friend relationships;
- private accounts;
- direct messages;
- nested comment replies;
- comment editing;
- reposts;
- bookmarks or saved public posts;
- custom or user-generated prompts;
- prompt categories or difficulty levels;
- location-based discovery;
- personalised recommendation ranking;
- leaderboards;
- public comparison of streaks;
- badges, levels, or achievements;
- subscriptions or payments;
- advertising;
- Android or web clients;
- cross-device draft synchronisation;
- video capture of the drawing process;
- digital drawing tools;
- complex image editing;
- a full moderation web console.

---

## 9. Access and authentication model

Authentication must never be required merely to launch the application, view the current Daily Prompt, browse public Submissions, open public Submission details, or view public profiles. A temporary authentication outage must not prevent those public read-only experiences when data is otherwise available or cached.

### 9.1 Guest capabilities

Without an account, a user may:

- open the app;
- view today’s Daily Prompt;
- browse the public feed;
- open public Submission details;
- view public profiles;
- begin a Sketch Session;
- use a countdown or No timer;
- take or select a photograph;
- review the photograph;
- save the work locally to continue later.

### 9.2 Account-required capabilities

An authenticated account is required to:

- publish a Submission;
- maintain a server-side Submission history;
- like or unlike a Submission;
- post a Reflection;
- delete a Reflection;
- report or block another user;
- edit a profile;
- receive a reliable personal streak;
- manage server-backed preferences;
- delete an account.

### 9.3 Authentication checkpoint

The app should not force registration before the user has experienced the core creative value.

When an unauthenticated user chooses **Submit to Community** or another action requiring an account, the app presents the **Save Your Creativity** screen. This screen explains that a free account is required to save the sketch to a history and share it with the community.

The screen includes:

- a thumbnail or preview of the user’s work;
- a concise benefit-led explanation;
- **Create Free Account** or equivalent primary action;
- **Sign In** for an existing user;
- **Continue Later** to preserve the work as a local draft and leave it unpublished.

After successful authentication, the app returns the user to the preserved review state and allows publication without requiring another photo or caption.

### 9.4 Account lifecycle

A user must be able to:

- create an account;
- sign in;
- remain signed in between launches;
- recover authentication through supported Descope flows;
- sign out;
- delete the account.

Usernames are unique and case-insensitive. The app should suggest a username during onboarding but allow the user to change it before completion.

---

## 10. Daily Prompt behaviour

### 10.1 Prompt composition

Each Daily Prompt contains exactly three words in a fixed display order.

Example:

1. Chocolate
2. Coffee
3. Banana

The creative instruction is to make one sketch inspired by the combination. A sketch may represent all three words literally, combine them conceptually, use only a subtle association, or interpret them abstractly. The product should not police the interpretation.

### 10.2 Shared prompt

All users receive the same Daily Prompt for the active Prompt Date. The app must never generate a different random set for each user or each app launch.

### 10.3 Prompt publication

Prompts should be prepared and published in advance. The Home screen should normally load today’s prompt independently of the feed so that community-feed latency does not delay the core creative action.

### 10.4 Historical availability

A published Prompt remains addressable after its date. Submissions retain their association with the original Prompt and Prompt Date.

A full historical prompt browser is not required in version one, but profile and detail screens must correctly display older prompt information.

### 10.5 Missing-prompt behaviour

If today’s prompt is temporarily unavailable:

- the app must show a clear recoverable state;
- the feed may remain usable;
- the client may retry;
- it must not invent a local prompt that could differ from the community prompt.

---

## 11. Information architecture and navigation

The primary iOS navigation has three destinations:

- **Home**
- **Profile**
- **Settings**

The Home screen contains the community feed, so a separate Feed tab is unnecessary in version one.

Secondary destinations and modal flows include:

- Timer Selection;
- Active Sketch Session;
- Camera or Photo Picker;
- Review Submission;
- Save Your Creativity authentication checkpoint;
- Submission Detail;
- Reflections thread/composer;
- another user’s Profile;
- profile editing;
- report and block actions.

The exact presentation style—sheet, full-screen cover, push navigation, or system controller—is defined in `design.md`.

---

## 12. Home screen requirements

The Home screen is the centre of the product and must immediately answer:

1. What should I create today?
2. What has the community created recently?

### 12.1 Today’s Inspiration section

The top of Home displays:

- **Today’s Inspiration** heading;
- supporting copy that makes clear the three words form one prompt;
- the three words as prominent visual cards;
- one primary creation action.

Before the user has published today:

- primary action: **Start Sketch**.

After the user has at least one published Submission for today:

- show a quiet completion acknowledgement such as **You sketched today**;
- provide **View My Sketch** or **View My Sketches**;
- provide **Create Another Sketch**.

If the user has multiple Submissions today, **View My Sketches** should open an appropriate list or the user’s profile filtered to today. A simpler first implementation may open the most recent Submission and allow navigation to the rest.

### 12.2 No timer controls on Home

Home must not show separate **Start Sketch** and **Skip Timer** buttons. Timer choice occurs only after Start Sketch, unless a remembered choice allows the app to begin directly.

### 12.3 Community feed placement

The community feed appears immediately below the inspiration and creation controls.

Version-one feed behaviour:

- public Submissions from all active users;
- newest first;
- cursor-paginated or infinite scrolling;
- no personalised ranking;
- no requirement that the feed contain only today’s prompt;
- prompt date and three-word context remain visible or accessible.

Today’s Submissions will naturally appear first when they are the newest. Older work can continue below, ensuring the feed is not empty at the start of a new Prompt Date.

### 12.4 Feed item content

A feed item includes:

- large sketch image or thumbnail;
- user avatar;
- display name or username;
- relative publication time;
- timer choice, such as **5 min** or **No timer**;
- compact reference to the three-word prompt;
- like control and count;
- Reflection control and count.

The artwork must remain visually dominant.

### 12.5 Home states

Home requires defined states for:

- loading prompt and feed;
- prompt loaded while feed loads;
- empty feed;
- feed error with prompt still usable;
- no network;
- today already completed;
- active unfinished session;
- local unpublished draft;
- account suspended or restricted.

---

## 13. Starting a Sketch Session

### 13.1 Default flow

When the user taps **Start Sketch**, the app presents a lightweight Timer Selection screen or sheet.

It asks:

> How long would you like to sketch?

Options:

- 1 minute
- 3 minutes
- 5 minutes
- 10 minutes
- No timer

The user selects exactly one option and taps **Start**.

### 13.2 Remember this choice

Timer Selection includes **Remember this choice**.

Rules:

- default is off;
- when off, the choice applies only to the current Sketch Session;
- when on, the selected choice becomes the user’s default;
- No timer can be remembered;
- a guest preference may be stored locally;
- an authenticated preference should be stored server-side and may also be cached locally;
- the user can change or clear the remembered preference in Settings.

When a preference is remembered, tapping **Start Sketch** should begin a session using that option without showing the selection sheet. The Home or Active Session experience must provide a discoverable **Change timer** path for future sessions; the current session’s original selection remains part of its record.

### 13.3 Session creation

A Sketch Session starts when the user confirms **Start** or when the app begins a remembered option.

The server should create or acknowledge the session as early as practical for authenticated users. Guests use a locally identified session until authentication or publication synchronises it.

The session records at least:

- Prompt;
- user or guest session identifier;
- timer mode;
- selected countdown duration, where applicable;
- start time;
- lifecycle state;
- later photo/upload/publication events.

---

## 14. Active Sketch Session

### 14.1 Countdown mode

The Active Sketch screen displays:

- the current prompt context;
- a large remaining time;
- Pause/Resume;
- Finish;
- Cancel.

When the countdown reaches zero:

- provide a gentle completion signal;
- offer the path to photograph the sketch;
- do not prevent the user from continuing to draw;
- preserve the fact that the selected timer completed.

### 14.2 No timer mode

No timer displays a calm **Sketching…** or **Sketch in progress** state rather than a target countdown.

It may show elapsed time, but the user should not feel pushed to stop. Controls include:

- Finish;
- Cancel.

### 14.3 Finish early

The user may finish before a countdown completes. The session records that the timer did not complete, but publication is not restricted or visually penalised.

### 14.4 Pause

Pause affects the visible countdown and records the pause state. The technical specification defines how server and client timestamps reconcile. Pausing is not available or necessary in No timer mode unless the design finds it useful.

### 14.5 Cancel

Cancel requires a lightweight confirmation when accidental loss is plausible.

The user may:

- abandon the session and return Home;
- continue sketching;
- where appropriate, preserve a local draft state.

### 14.6 App interruption and recovery

Ordinary interruptions must not destroy the session:

- app backgrounding;
- screen lock;
- incoming call;
- temporary loss of network;
- app termination and relaunch, where recoverable.

On return, the app offers to resume the active session or continue to photo capture if the user had already finished.

---

## 15. Photo capture and selection

After Finish or timer completion, the user can:

- take a new photograph with the camera;
- choose an existing photograph from the photo library;
- cancel and return to the Sketch Session;
- retry after permission or capture failure.

The app should guide the user towards a clear, well-lit, correctly oriented image without requiring sophisticated editing.

Version-one image adjustment may include system-provided crop or rotation where straightforward, but custom filters and drawing edits are out of scope.

A user who denies camera permission should still be able to select an existing image, and the app must explain how to change permissions in Settings.

---

## 16. Review Submission flow

### 16.1 Purpose

The Review Submission screen is a required step before publication. It gives the user confidence that the captured image is good enough and prevents accidental sharing.

The Stitch screen titled **Ready to share?** is the visual reference. The internal feature name is **Review Submission**.

### 16.2 Required content

Display:

- a large image preview;
- the Prompt Date and three prompt words;
- timer choice;
- an action to retake or replace the image;
- an optional caption field;
- **Submit to Community**;
- **Save for Later** or equivalent secondary action where a recoverable draft can be retained.

### 16.3 Caption

Caption rules:

- optional;
- plain text;
- concise maximum length defined in the API contract;
- no rich text;
- no hashtags, mentions, or links required in version one.

### 16.4 Signed-in publication

For an authenticated user, **Submit to Community** begins upload and publication.

The screen shows:

- upload progress;
- safe retry after a recoverable failure;
- clear success state;
- no duplicate Submission if a request times out and is retried.

After success, the app returns to Home or opens the new Submission Detail, according to `design.md`. Home must reflect the new Submission promptly.

### 16.5 Guest publication

For a guest, **Submit to Community** presents **Save Your Creativity**.

The photo, caption, Prompt, and Sketch Session state must remain intact while the user creates an account or signs in.

### 16.6 Continue later

A user may choose to continue later.

Version-one guarantee:

- the image and necessary metadata are preserved locally as a Draft;
- Home indicates that an unpublished Draft exists;
- the user can return to review and publish it;
- a guest can later authenticate and publish;
- cross-device access is not promised.

The app should avoid retaining large abandoned Drafts indefinitely. The retention and cleanup behaviour is defined in the technical specifications.

---

## 17. Submission publication rules

A published Submission has:

- one owner;
- one Daily Prompt;
- one image;
- normally one Sketch Session;
- an optional caption;
- a timer mode and selected duration inherited from the session;
- publication timestamp;
- like count;
- Reflection count;
- moderation state.

A user may publish multiple Submissions for the same Prompt Date. Each must be a separate Submission, normally linked to a separate Sketch Session.

A published Submission is public within the app by default in version one. Private Submissions and private profiles are out of scope.

A user can delete their own Submission. Deletion removes it from public feeds, profile galleries, and detail access. Associated moderation and operational records may be retained where necessary, but the image must follow the documented deletion policy.

Editing a published image is out of scope. Editing a caption after publication is also out of scope for version one; the user may delete and republish if needed.

---

## 18. Submission Detail

The Submission Detail screen displays:

- full-size artwork;
- owner avatar, display name, and username;
- all three prompt words;
- Prompt Date;
- selected timer or No timer;
- optional caption;
- like control and count;
- Reflection control and count;
- Reflection thread;
- native Share action;
- overflow menu for owner actions, reporting, and blocking as appropriate.

The Stitch title may use a caption-derived or generic title, but a formal Submission title is not required in version one.

From Submission Detail, the user can:

- open the owner’s profile;
- like or unlike;
- read Reflections;
- add a Reflection when authenticated;
- share through the iOS share sheet;
- delete their own Submission;
- report content;
- block the owner, when not viewing their own content.

---

## 19. Likes

### 19.1 Behaviour

An authenticated user can like a public Submission and remove that like.

Rules:

- at most one active Like per user per Submission;
- tapping an unliked heart likes it;
- tapping a liked heart unlikes it;
- the displayed count updates promptly;
- retries must not create duplicate Likes;
- guests tapping Like are taken through authentication and returned to the same Submission; after successful authentication and profile completion, the app should complete or explicitly resume the intended Like action.

No list of everyone who liked a Submission is required in version one.

### 19.2 Product role

Likes are supportive feedback, not a ranking system. The feed remains chronological. Like count must not determine version-one feed ordering.

---

## 20. Reflections

### 20.1 Behaviour

A Reflection is a short, public, plain-text response to a Submission.

Version-one rules:

- authentication required to post;
- displayed oldest-to-newest in the detail thread, with a practical loading strategy;
- one level only; no replies or threading;
- no editing;
- author can delete their own Reflection;
- Submission owner may report a Reflection and may hide it from their own work if the moderation model supports that action;
- character limit defined in the API contract;
- empty or whitespace-only content rejected.

### 20.2 Guest interaction

A guest can read Reflections. Attempting to post invokes authentication while preserving the draft text, the intended Submission, and the return location. After successful authentication and profile completion, the app resumes the Reflection action rather than merely returning to a generic screen.

### 20.3 Counts

Feed and detail screens show the active Reflection count. Deleted or moderated Reflections do not count.

### 20.4 Tone

The UI should encourage constructive, human responses. Placeholder copy such as **Add a reflection…** is preferred to high-pressure engagement language.

---

## 21. Profiles

### 21.1 Public profile content

A public profile shows:

- avatar;
- display name;
- unique username;
- optional short bio;
- total published Submission count;
- current streak;
- artwork gallery in reverse chronological order.

A profile does not show follower counts because following is not part of version one.

### 21.2 Own profile

The authenticated user’s profile additionally provides:

- Edit Profile;
- settings access;
- New Submission/Create Another action;
- deletion controls through individual Submission details.

### 21.3 Profile gallery

Each gallery item shows the artwork and enough context to distinguish dates or prompts. Tapping opens Submission Detail.

Pagination is required for users with many Submissions.

### 21.4 Streak definition

A user has participated on a Prompt Date when at least one active published Submission belongs to that date.

Current streak:

- counts consecutive Prompt Dates;
- may end on today or yesterday so a user is not shown as having lost the streak before today is over;
- multiple Submissions on a date count once;
- Drafts do not count;
- an abandoned Sketch Session does not count;
- deleting the final Submission for a date may change the streak;
- should be displayed as personal progress, not compared publicly in rankings.

---

## 22. Settings and preferences

Settings includes:

### Account

- avatar and profile summary;
- Edit Profile;
- email or identity summary where appropriate;
- Sign Out;
- Delete Account.

### Timezone

Display the timezone used for daily reminder scheduling and date presentation. The global Daily Prompt boundary remains the same for all users.

### Notifications

- Daily Reminder on/off;
- Reminder Time;
- explanation that the reminder announces the daily prompt.

### Timer preference

- remember timer option on/off;
- remembered countdown or No timer;
- clear/change preference.

### Appearance

- System;
- Light;
- Dark.

### Support and legal

- Help & Support;
- Community Guidelines;
- Privacy;
- Terms;
- About Daily Sketch;
- app version.

A **Canvas Default Setup** setting shown in the Stitch concept is not needed because Daily Sketch does not provide a digital canvas. It should not be implemented unless the product scope later changes.

---

## 23. Notifications

### 23.1 Daily reminder

Version one supports a configurable daily reminder.

Example copy:

> Today’s inspiration is ready.

The user can enable or disable the reminder and choose a local reminder time. Tapping it opens Home.

Local iOS notifications are acceptable for version one because the reminder schedule is predictable. The architecture may support remote push later.

### 23.2 Social activity events

The backend should be capable of recording activity events for:

- a Like on the user’s Submission;
- a Reflection on the user’s Submission.

A full Activity inbox and social push notifications are not required for the first release unless implementation capacity allows. Their absence must not block likes or Reflections.

---

## 24. Native sharing

Submission Detail provides the iOS system Share action.

The share payload should contain an appropriate combination of:

- rendered sketch image or share image;
- prompt words;
- attribution to the creator;
- deep link or public link when available;
- simple Daily Sketch branding.

Version one should use the native share sheet rather than bespoke integrations for individual social platforms.

Sharing does not change the Submission’s public state and should not expose private tokens or storage URLs.

---

## 25. Safety, reporting, and blocking

A public image-and-comment community requires baseline safety controls in version one.

### 25.1 Reporting

An authenticated user can report:

- a Submission;
- a Reflection;
- a user profile.

Initial reasons may include:

- inappropriate content;
- harassment or abuse;
- hate or hateful conduct;
- spam;
- intellectual-property concern;
- self-harm concern;
- other.

The reporter receives confirmation but not private moderation details.

### 25.2 Blocking

An authenticated user can block another user.

Expected effect:

- blocked user’s Submissions are hidden from the blocker’s feed and profile browsing;
- blocked user’s Reflections are hidden from the blocker;
- the blocker cannot Like or comment on the blocked user’s content;
- reciprocal interaction restrictions should be enforced where practical;
- blocking can be reversed in Settings or a blocked-users screen.

### 25.3 Administrative moderation

A complete moderation dashboard is not required, but authorised operators must be able to:

- inspect reports;
- remove a Submission;
- remove a Reflection;
- suspend or disable an account;
- restore content when appropriate;
- record the reason for an action.

### 25.4 Community tone

The product should make it clear that constructive, supportive participation is expected. The interface should avoid rewarding provocation or conflict.

---

## 26. Product analytics and session timing

### 26.1 Required funnel events

The product should measure, with appropriate privacy controls:

- app opened;
- prompt viewed;
- Start Sketch tapped;
- timer option selected;
- Sketch Session started;
- session paused/resumed;
- timer completed;
- session finished early;
- session abandoned;
- photo captured or selected;
- Review Submission viewed;
- authentication checkpoint shown;
- Draft saved;
- upload started/completed/failed;
- Submission published;
- feed viewed;
- Submission Detail viewed;
- Like added/removed;
- Reflection posted/deleted;
- profile viewed;
- reminder enabled/disabled.

### 26.2 Server-authoritative timing

For authenticated or synchronised sessions, record server timestamps at meaningful lifecycle points, including:

- session creation/start;
- upload initiation;
- upload completion;
- Submission creation.

Where available, the client may additionally report photo-capture time and local lifecycle events.

### 26.3 Interpretation

Derived values may include:

- elapsed time from session start to photo;
- elapsed time from session start to publication;
- upload duration;
- conversion from session start to published Submission;
- completion by timer option.

These are elapsed intervals, not guaranteed active drawing time.

### 26.4 User-facing analytics

Detailed personal analytics are not required in version one. The only required user-facing habit measure is the streak and basic Submission count.

---

## 27. Privacy and data behaviour

### 27.1 Public data

In version one, the following are public within the app:

- username;
- display name;
- avatar;
- bio;
- published Submissions;
- captions;
- Likes as counts;
- Reflections;
- streak and Submission count.

Email addresses, Descope identifiers, notification settings, blocked-user relationships, Drafts, and Sketch Session analytics are not public.

### 27.2 Image metadata

The app should remove unnecessary EXIF metadata, particularly precise location, before public display or derivative generation.

### 27.3 Account deletion

The user can request account deletion from Settings. The product must clearly explain that public content and profile access will be removed and that final deletion may take a documented period.

### 27.4 Data minimisation

Do not collect precise location in version one. Do not require real names. Do not collect contacts.

---

## 28. Accessibility and inclusive behaviour

Daily Sketch must support:

- Dynamic Type;
- VoiceOver labels and logical reading order;
- sufficient colour contrast;
- controls with suitable touch targets;
- reduced-motion preferences;
- system Light and Dark appearance;
- clear alternatives when camera permission is unavailable;
- status communication that does not rely on colour alone;
- accessible timer announcements without excessive interruption.

User-created artwork does not require alt text in version one, but the architecture and product may later support an optional accessibility description.

The product should avoid language that assumes artistic skill or judges quality. Copy should invite experimentation.

---

## 29. Loading, empty, error, and recovery states

Every core flow requires explicit non-happy-path behaviour.

### Home

- prompt loading;
- feed loading;
- feed empty;
- feed retry;
- prompt unavailable;
- offline with cached prompt;
- active session recovery;
- pending Draft.

### Authentication

- cancelled authentication;
- unavailable provider;
- duplicate username;
- expired session;
- successful return to preserved action.

### Camera and photo library

- permission denied;
- no camera available;
- image selection cancelled;
- unsupported or corrupt image;
- memory pressure with large image.

### Upload and publication

- network interrupted;
- signed upload expired;
- upload retry;
- publication request timed out;
- duplicate-safe retry;
- moderated/rejected image;
- Draft preservation.

### Social actions

- optimistic Like rollback;
- failed Reflection post with text preserved;
- deleted Submission while open;
- blocked or suspended user;
- unavailable profile.

Errors should explain the next useful action rather than expose technical details.

---

## 30. Product success measures

Version-one success should be evaluated primarily on whether the product creates a repeatable creative habit and a healthy loop between creation and discovery.

### Activation

- percentage of new users who view the prompt;
- percentage who start a Sketch Session;
- percentage who reach Review Submission;
- percentage who create an account after the guest flow;
- percentage who publish a first Submission.

### Habit and retention

- daily and weekly active creators;
- seven-day and thirty-day retention;
- average participating Prompt Dates per active user;
- streak distribution without using it as a competitive target;
- reminder opt-in and reminder-to-session conversion.

### Creative funnel

- session-to-photo conversion;
- photo-to-publication conversion;
- abandonment by stage;
- timer-option distribution;
- No timer usage;
- multiple Submissions per Prompt Date;
- median elapsed session interval.

### Community health

- feed views after publication;
- profile views;
- percentage of Submissions receiving a Like or Reflection;
- Reflections per active creator;
- report rate;
- block rate;
- moderation turnaround.

Raw engagement should not override the product’s calm, supportive character.

---

## 31. End-to-end acceptance journeys

Version one is product-complete only when the following journeys work on a physical iPhone.

### 31.1 Guest creator becomes a member

1. Open the app without an account.
2. View today’s three-word prompt.
3. Browse recent community Submissions.
4. Tap Start Sketch.
5. Choose 3 minutes without remembering it.
6. Complete or finish the session.
7. Take a photograph.
8. Review and replace the photo if needed.
9. Add a caption.
10. Tap Submit to Community.
11. See Save Your Creativity.
12. Create an account through Descope.
13. Choose a unique username and display name.
14. Return to the preserved review state.
15. Publish successfully.
16. See the new Submission on Home and the profile.

### 31.2 Returning creator with remembered timer

1. Open Home while authenticated.
2. See today’s prompt.
3. Tap Start Sketch.
4. Begin the remembered 5-minute timer directly.
5. Background and reopen the app.
6. Resume the correct session state.
7. Finish early.
8. Choose an existing photo.
9. Publish.
10. See **You sketched today** with View My Sketch and Create Another Sketch.

### 31.3 Multiple Submissions

1. Publish one Submission for today.
2. Tap Create Another Sketch.
3. choose No timer;
4. create and publish a second Submission;
5. see both in the user’s profile;
6. ensure the streak counts the date once.

### 31.4 Social interaction

1. Open another user’s Submission.
2. Like it.
3. Add a Reflection.
4. See counts update.
5. Delete the Reflection.
6. Share the Submission through the native share sheet.
7. Open the user’s profile and browse older work.

### 31.5 Draft and recovery

1. Start a session while offline or as a guest.
2. Capture a photo.
3. choose Continue Later or encounter an upload failure;
4. return Home;
5. reopen the Draft;
6. authenticate if required;
7. publish without retaking the photo.

### 31.6 Safety and ownership

1. Report an inappropriate Submission or Reflection.
2. Block its owner.
3. confirm their content is hidden from the blocker’s experience;
4. delete one of the current user’s own Submissions;
5. confirm it disappears from feed and profile;
6. request account deletion from Settings.

---

## 32. Future product direction

Potential later releases may add:

- following and friend relationships;
- a Following feed;
- an Activity inbox and social push notifications;
- prompt history browsing and date-specific galleries;
- curated themes or prompt packs;
- personal statistics beyond streaks;
- collaborative or group challenges;
- saved public Submissions;
- nested replies;
- richer sharing assets;
- web profiles;
- Android support;
- optional private profiles;
- recommendation ranking;
- location-based communities;
- recorded time-lapse or drawing-process video;
- optional AI-assisted prompt curation.

Future work should preserve the two essential Home questions:

1. What should I create today?
2. What has the community created?

---

## 33. Canonical version-one decisions

For clarity, the following decisions are settled for the first implementation:

- The product is a native iOS app.
- Every user receives the same three words for each Prompt Date.
- All three words form one prompt; users do not select one word.
- Home has one Start Sketch action, not a separate Skip Timer action.
- Timer choices are 1, 3, 5, 10 minutes, or No timer.
- Remember this choice defaults to off.
- Actual lifecycle timestamps are tracked even in No timer mode.
- Users may make multiple Submissions for one Prompt Date.
- The app can be launched and the Daily Prompt and public community can be viewed without authentication.
- Guests may complete the creative and review flow before authenticating.
- Authentication is required to publish and participate socially.
- Review Submission remains a dedicated screen.
- Save Your Creativity remains the guest authentication checkpoint.
- Version one includes a chronological public feed.
- Version one includes Likes and Reflections.
- Version one includes public profiles and personal streaks.
- Version one includes native sharing.
- Version one does not include following, private accounts, DMs, or ranking algorithms.
- PostgreSQL-backed technical behaviour, API details, and implementation order are defined in the companion specifications.
