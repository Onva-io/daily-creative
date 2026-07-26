import Foundation

/// Rules for when cached home inspiration should be hidden while a fresh prompt loads.
///
/// Stale after 15 minutes asleep, or when the global Prompt Date boundary (00:00 UTC) has
/// been crossed since the cache was written — see ADR 0005.
enum PromptFreshness {
    static let maxAge: TimeInterval = 15 * 60

    static var utcCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    /// Whether cached words should be cleared immediately before refreshing.
    static func shouldHideCachedPrompt(
        cachedAt: Date,
        promptDate: Date?,
        now: Date
    ) -> Bool {
        if now.timeIntervalSince(cachedAt) >= maxAge {
            return true
        }
        if !utcCalendar.isDate(cachedAt, inSameDayAs: now) {
            return true
        }
        if let promptDate, !utcCalendar.isDate(promptDate, inSameDayAs: now) {
            return true
        }
        return false
    }
}
