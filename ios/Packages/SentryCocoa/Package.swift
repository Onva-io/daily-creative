// swift-tools-version: 5.9
import PackageDescription

// sentry-cocoa's upstream Package.swift declares every xcframework variant as a
// binary target. SwiftPM downloads all of them (~1 GB) even when the app only
// links one product, which routinely fails Xcode package resolution.
//
// Use the dynamic xcframework (not static): Xcode 16 requires a dSYM for every
// bundled Sentry.framework UUID, and only the dynamic slice ships DWARF.
let package = Package(
    name: "SentryCocoa",
    platforms: [.iOS("18.0")],
    products: [
        .library(name: "Sentry", targets: ["Sentry-Dynamic"]),
    ],
    targets: [
        .binaryTarget(
            name: "Sentry-Dynamic",
            url: "https://github.com/getsentry/sentry-cocoa/releases/download/8.58.4/Sentry-Dynamic.xcframework.zip",
            checksum: "23c14f81d67be79b3dd07ca739a96f2f574f7d7e2ae9e585e99058c6c3ca89e7" // pragma: allowlist secret
        ),
    ]
)
