// swift-tools-version: 5.9
import PackageDescription

// sentry-cocoa's upstream Package.swift declares every xcframework variant as a
// binary target. SwiftPM downloads all of them (~1 GB) even when the app only
// links `Sentry`, which routinely fails Xcode package resolution.
// This wrapper depends on the single static xcframework we actually use.
let package = Package(
    name: "SentryCocoa",
    platforms: [.iOS("18.0")],
    products: [
        .library(name: "Sentry", targets: ["Sentry"]),
    ],
    targets: [
        .binaryTarget(
            name: "Sentry",
            url: "https://github.com/getsentry/sentry-cocoa/releases/download/8.58.4/Sentry.xcframework.zip",
            checksum: "8cdee7ae675910381bb53e6c84d61256c54fffb0ad039c9172c78e1029c70c29" // pragma: allowlist secret
        ),
    ]
)
