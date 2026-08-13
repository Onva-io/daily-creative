import Foundation
import Observation
@preconcurrency import DailyCreativeAPI

/// Persists a guest age declaration in Keychain and holds the server-issued
/// community-capability token. Date of birth is never written to UserDefaults.
@MainActor
@Observable
final class GuestAgeGateStore {
    static let shared = GuestAgeGateStore()

    private let defaults: UserDefaults
    private let minimumAgeKey = "guest.minimumAge"
    private let dateAccount = "guest.declaredDateOfBirth"
    private let tokenAccount = "guest.ageToken"
    private let expiresAccount = "guest.ageTokenExpiresAt"
    private let legacyDateKey = "guest.declaredDateOfBirth"

    private(set) var declaredDateOfBirth: Date?
    private(set) var minimumAge: Int
    private(set) var guestAgeToken: String?
    private(set) var tokenExpiresAt: Date?

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.minimumAge = defaults.object(forKey: minimumAgeKey) as? Int ?? 13
        self.declaredDateOfBirth = Self.loadDate(account: dateAccount)
        self.guestAgeToken = Self.loadString(account: tokenAccount)
        self.tokenExpiresAt = Self.loadDate(account: expiresAccount)
        migrateLegacyUserDefaultsIfNeeded(defaults: defaults)
        applyTokenHeader()
    }

    var needsAgeDeclaration: Bool {
        declaredDateOfBirth == nil || !hasValidToken
    }

    var isUnderMinimumAge: Bool {
        guard let declaredDateOfBirth else { return false }
        return age(on: Date(), dateOfBirth: declaredDateOfBirth) < minimumAge
    }

    var canBrowseCommunity: Bool {
        declaredDateOfBirth != nil && hasValidToken && !isUnderMinimumAge
    }

    private var hasValidToken: Bool {
        guard guestAgeToken != nil, let tokenExpiresAt else { return false }
        return tokenExpiresAt > Date()
    }

    func setMinimumAge(_ age: Int) {
        minimumAge = max(1, age)
        defaults.set(minimumAge, forKey: minimumAgeKey)
    }

    func declare(dateOfBirth: Date) async throws {
        let today = Calendar.current.startOfDay(for: Date())
        let dob = Calendar.current.startOfDay(for: dateOfBirth)
        guard dob <= today else {
            throw ProfileAPIError.underlying("Date of birth cannot be in the future.")
        }
        if age(on: today, dateOfBirth: dob) < minimumAge {
            throw ProfileAPIError.underMinimumAge(
                "You must be at least \(minimumAge) years old to use this app."
            )
        }

        DailyCreativeAPIClientConfig.configure(baseURL: AppEnvironment.current.apiBaseURL)
        let request = SetDateOfBirthRequest(dateOfBirth: Self.isoDateString(from: dob))
        let response: GuestAgeDeclaration
        do {
            response = try await GuestAPI.declareGuestAge(setDateOfBirthRequest: request)
        } catch {
            throw Self.mapAPIError(error)
        }

        declaredDateOfBirth = dob
        guestAgeToken = response.guestAgeToken
        tokenExpiresAt = response.expiresAt
        minimumAge = response.minimumAge
        defaults.set(minimumAge, forKey: minimumAgeKey)
        try Self.saveDate(dob, account: dateAccount)
        try Self.saveString(response.guestAgeToken, account: tokenAccount)
        try Self.saveDate(response.expiresAt, account: expiresAccount)
        applyTokenHeader()
    }

    func applyTokenHeader() {
        guard hasValidToken, let guestAgeToken else {
            DailyCreativeAPITokenBridge.clearGuestAgeToken()
            return
        }
        DailyCreativeAPITokenBridge.setGuestAgeToken(guestAgeToken)
    }

    func age(on today: Date = Date(), dateOfBirth: Date) -> Int {
        Calendar.current.dateComponents(
            [.year],
            from: Calendar.current.startOfDay(for: dateOfBirth),
            to: Calendar.current.startOfDay(for: today)
        ).year ?? 0
    }

    private func migrateLegacyUserDefaultsIfNeeded(defaults: UserDefaults) {
        guard declaredDateOfBirth == nil,
              let stored = defaults.object(forKey: legacyDateKey) as? Date else { return }
        declaredDateOfBirth = Calendar.current.startOfDay(for: stored)
        try? Self.saveDate(declaredDateOfBirth!, account: dateAccount)
        defaults.removeObject(forKey: legacyDateKey)
        // Token is required for community reads; the overlay stays until re-declare.
    }

    private static func isoDateString(from date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    private static func mapAPIError(_ error: Error) -> Error {
        if let errorResponse = error as? ErrorResponse {
            switch errorResponse {
            case .error(let code, let data, _, _):
                if let data,
                   let envelope = try? JSONDecoder().decode(GuestAPIErrorEnvelope.self, from: data) {
                    switch envelope.error.code {
                    case "under_minimum_age":
                        return ProfileAPIError.underMinimumAge(envelope.error.message)
                    default:
                        return ProfileAPIError.underlying(envelope.error.message)
                    }
                }
                _ = code
            }
        }
        return ProfileAPIError.underlying(error.localizedDescription)
    }

    private static func saveDate(_ date: Date, account: String) throws {
        try KeychainStore.save(account: account, data: iso8601.string(from: date).data(using: .utf8)!)
    }

    private static func saveString(_ value: String, account: String) throws {
        try KeychainStore.save(account: account, data: Data(value.utf8))
    }

    private static func loadDate(account: String) -> Date? {
        guard let data = try? KeychainStore.load(account: account),
              let raw = String(data: data, encoding: .utf8) else { return nil }
        return iso8601.date(from: raw)
    }

    private static func loadString(account: String) -> String? {
        guard let data = try? KeychainStore.load(account: account) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private static let iso8601: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()
}

private struct GuestAPIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}
