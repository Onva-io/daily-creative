# App Store Metadata Template

**App name:** Daily Sketch
**Subtitle:** Daily three-word sketch journal
**Primary category:** Photo & Video
**Secondary category:** Social Networking

## URLs (owner-supplied)

- Support URL: `SUPPORT_URL` in Release xcconfig
- Support email: `SUPPORT_EMAIL` (required for Guideline 1.2 published contact)
- Privacy: `PRIVACY_URL` (backend `/api/v1/policies/privacy/html`)
- Terms: `TERMS_URL` (backend `/api/v1/policies/terms/html`)
- Community guidelines: `COMMUNITY_GUIDELINES_URL`

In App Store Connect, attach the custom EULA / Terms URL so it matches the in-app gated policy version.

## Description (draft)

Daily Sketch gives everyone the same three-word prompt each day. Sketch on paper, photograph your work, and share with a creative community. Guests can explore today's prompt before creating a free account. Community browsing requires an age declaration; publishing requires accepting the latest Terms, Privacy Policy, and Community Guidelines.

## Keywords

sketch, drawing, daily prompt, creativity, journal, art community

## Screenshots

Capture on physical device for required sizes (6.7", 6.5", 5.5"). Use Stitch references in `spec/stitch_daily_sketch_journal.zip` for composition guidance — Home, timer, session, confirm, Save Your Creativity, detail, profile, settings.

## Age rating

Apple now uses five age rating tiers: **4+, 9+, 13+, 16+, 18+**.

Complete the App Store Connect questionnaire carefully. This app includes:
- User-generated content (images, text stories, reflections)
- Unrestricted web access: No
- Reporting and blocking: Yes
- Proactive content filtering + 24-hour moderation SLA: Yes
- Minimum age: 13+

Expect at least a **13+** rating given unrestricted UGC; higher if mature content frequency warrants it. Re-run the questionnaire whenever policy or feature changes affect the content elements that led to the rating (significant change under state app-store accountability acts).
