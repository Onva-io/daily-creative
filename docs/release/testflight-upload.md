# TestFlight Upload Runbook

## Prerequisites (owner)

- Apple Developer Team ID in signing configuration
- App Store Connect app record
- Distribution certificate + App Store provisioning profile
- Release Staging or Release Production scheme selected
- Release xcconfigs use real values (no `replace-me` placeholders, no localhost URLs). Run `make ios-config-check` before archiving; the same check runs as an Xcode pre-build script for Release-* configurations.

## Archive

1. `make ios-generate`
2. Open `ios/DailySketch.xcodeproj`
3. Select scheme **DailySketch**, configuration **Release-Staging**
4. Product → Archive
5. Validate archive
6. Distribute → App Store Connect → Upload

If the archive fails with an iOS release config error, fix `DESCOPE_PROJECT_ID` (and other required keys) in the matching `ios/Config/**/Release-*.xcconfig` and regenerate.

## Traceability

Record in App Store Connect release notes:

- iOS `MARKETING_VERSION` / build number
- Backend `/health/version` output from matching staging deploy
- Git commit SHA

## In-repo readiness

Configs, Privacy Manifest, and metadata templates are present. Live upload requires owner credentials and is not claimed by CI. Mock authentication is intentionally limited to Debug Local/Development and must never appear in a TestFlight or App Store build.
