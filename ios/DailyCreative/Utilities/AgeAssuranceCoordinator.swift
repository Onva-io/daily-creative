import Foundation

/// Thin wrapper around Apple age-assurance APIs.
/// Declared Age Range requires the iOS 26.2 SDK and the
/// `com.apple.developer.declared-age-range` entitlement. Until the project
/// builds against that SDK, this coordinator is a no-op stub so iOS 18
/// deployment targets keep compiling. Wire the real calls when Xcode 26.2+
/// is the team build toolchain.
enum AgeAssuranceCoordinator {
    @MainActor
    static func acknowledgeSignificantChangesIfNeeded(documents: [PolicyDocumentSummary]) async {
        // When DeclaredAgeRange is linked:
        // - check AgeRangeService.shared.requiredRegulatoryFeatures
        // - call showSignificantUpdateAcknowledgment for adult notification
        // - use PermissionKit SignificantAppUpdateTopic for parental consent
        _ = documents
    }

    @MainActor
    static func requestDeclaredAgeRangeIfEligible() async -> ClosedRange<Int>? {
        // When DeclaredAgeRange is linked and isEligibleForAgeFeatures is true,
        // request ageGates 13/16/18 and return the shared range.
        return nil
    }
}
