import Foundation

/// Protocol defining product-specific configuration.
/// Each app target (DailySketch, DailyStory) provides its own conforming value,
/// driven by Info.plist keys set in xcconfig files.
protocol ProductConfiguring: Sendable {
    /// The human-readable product name (e.g. "Daily Sketch", "Daily Story").
    var brandName: String { get }
    /// The creative type identifier matching the API's `creative_type` enum.
    var creativeTypeID: String { get }
    /// Navigation title for the home screen.
    var homeTitle: String { get }
    /// Community feed section title.
    var communityTitle: String { get }
    /// Primary CTA for starting today's creative session.
    var startActionTitle: String { get }
    /// Text used in share payloads.
    var shareFooter: String { get }
    /// Analytics event prefix.
    var analyticsPrefix: String { get }
    /// Whether this product uses camera/photo capture.
    var requiresCamera: Bool { get }
    /// Local notification identifier for the daily reminder.
    var dailyReminderNotificationId: String { get }
}

/// Info.plist-driven ProductConfig loaded from the main bundle.
struct ProductConfig: ProductConfiguring {
    let brandName: String
    let creativeTypeID: String
    let homeTitle: String
    let communityTitle: String
    let startActionTitle: String
    let shareFooter: String
    let analyticsPrefix: String
    let requiresCamera: Bool
    let dailyReminderNotificationId: String

    /// Load configuration from the main bundle's Info.plist.
    /// Falls back to DailySketch defaults if keys are missing.
    static let current: ProductConfig = {
        let bundle = Bundle.main
        let brand = bundle.object(forInfoDictionaryKey: "BRAND_NAME") as? String ?? "Daily Sketch"
        let creativeType = bundle.object(forInfoDictionaryKey: "CREATIVE_TYPE_ID") as? String ?? "sketch"
        let communityTitle = bundle.object(forInfoDictionaryKey: "COMMUNITY_TITLE") as? String ?? "Community Sketches"
        let startActionTitle = bundle.object(forInfoDictionaryKey: "START_ACTION_TITLE") as? String ?? "Start Sketch"
        let requiresCamera = (bundle.object(forInfoDictionaryKey: "REQUIRES_CAMERA") as? String)?.uppercased() == "YES"
        let dailyReminderNotificationId = bundle.object(forInfoDictionaryKey: "DAILY_REMINDER_NOTIFICATION_ID") as? String
            ?? "daily-sketch.daily-reminder"
        return ProductConfig(
            brandName: brand,
            creativeTypeID: creativeType,
            homeTitle: brand,
            communityTitle: communityTitle,
            startActionTitle: startActionTitle,
            shareFooter: "Created with \(brand)",
            analyticsPrefix: creativeType,
            requiresCamera: requiresCamera,
            dailyReminderNotificationId: dailyReminderNotificationId
        )
    }()
}
