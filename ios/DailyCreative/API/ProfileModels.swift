import Foundation

enum UsernameValidator {
    static func isValidFormat(_ username: String) -> Bool {
        let trimmed = username.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 3, trimmed.count <= 30 else { return false }
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        return trimmed.unicodeScalars.allSatisfy { allowed.contains($0) }
    }

    static func validationMessage(for username: String) -> String? {
        let trimmed = username.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return "Choose a username."
        }
        if trimmed.count < 3 {
            return "Usernames must be at least 3 characters."
        }
        if trimmed.count > 30 {
            return "Usernames must be 30 characters or fewer."
        }
        if !isValidFormat(trimmed) {
            return "Use only letters, numbers, and underscores."
        }
        return nil
    }
}

enum TimerPreferenceOption: String, CaseIterable, Identifiable, Sendable {
    case oneMinute = "1 minute"
    case threeMinutes = "3 minutes"
    case fiveMinutes = "5 minutes"
    case tenMinutes = "10 minutes"
    case noTimer = "No timer"

    var id: String { rawValue }

    var mode: String {
        self == .noTimer ? "no_timer" : "countdown"
    }

    var seconds: Int? {
        switch self {
        case .oneMinute: 60
        case .threeMinutes: 180
        case .fiveMinutes: 300
        case .tenMinutes: 600
        case .noTimer: nil
        }
    }

    static func from(mode: String?, seconds: Int?) -> TimerPreferenceOption? {
        if mode == "no_timer" { return .noTimer }
        guard mode == "countdown", let seconds else { return nil }
        switch seconds {
        case 60: return .oneMinute
        case 180: return .threeMinutes
        case 300: return .fiveMinutes
        case 600: return .tenMinutes
        default: return nil
        }
    }
}

struct UserPreferencesModel: Equatable, Sendable {
    var notificationsEnabled: Bool
    var notificationTimeLocal: String?
    var timezone: String
    var rememberTimerOption: Bool
    var rememberedTimerMode: String?
    var rememberedTimerSeconds: Int?
    var appearance: String

    static let defaults = UserPreferencesModel(
        notificationsEnabled: false,
        notificationTimeLocal: nil,
        timezone: "UTC",
        rememberTimerOption: false,
        rememberedTimerMode: nil,
        rememberedTimerSeconds: nil,
        appearance: "system"
    )
}

enum ProfileAPIError: LocalizedError, Equatable {
    case usernameTaken
    case usernameInvalid
    case usernameReserved
    case invalidTimerPreference
    case sessionExpired
    case underlying(String)

    var errorDescription: String? {
        switch self {
        case .usernameTaken:
            return "That username is already taken."
        case .usernameInvalid:
            return "Usernames must be 3–30 characters and use only letters, numbers, and underscores."
        case .usernameReserved:
            return "That username is reserved."
        case .invalidTimerPreference:
            return "Timer preference mode and seconds are inconsistent."
        case .sessionExpired:
            return AuthServiceError.sessionExpired.localizedDescription
        case .underlying(let message):
            return message
        }
    }
}
