import Foundation
import Observation

/// Persists a guest age declaration so community content can be gated without forcing signup.
@MainActor
@Observable
final class GuestAgeGateStore {
    static let shared = GuestAgeGateStore()

    private let defaults: UserDefaults
    private let dateKey = "guest.declaredDateOfBirth"
    private let minimumAgeKey = "guest.minimumAge"

    private(set) var declaredDateOfBirth: Date?
    private(set) var minimumAge: Int

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.minimumAge = defaults.object(forKey: minimumAgeKey) as? Int ?? 13
        if let stored = defaults.object(forKey: dateKey) as? Date {
            self.declaredDateOfBirth = stored
        }
    }

    var needsAgeDeclaration: Bool {
        declaredDateOfBirth == nil
    }

    var isUnderMinimumAge: Bool {
        guard let declaredDateOfBirth else { return false }
        return age(on: Date(), dateOfBirth: declaredDateOfBirth) < minimumAge
    }

    var canBrowseCommunity: Bool {
        declaredDateOfBirth != nil && !isUnderMinimumAge
    }

    func setMinimumAge(_ age: Int) {
        minimumAge = max(1, age)
        defaults.set(minimumAge, forKey: minimumAgeKey)
    }

    func declare(dateOfBirth: Date) throws {
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
        declaredDateOfBirth = dob
        defaults.set(dob, forKey: dateKey)
    }

    func age(on today: Date = Date(), dateOfBirth: Date) -> Int {
        Calendar.current.dateComponents(
            [.year],
            from: Calendar.current.startOfDay(for: dateOfBirth),
            to: Calendar.current.startOfDay(for: today)
        ).year ?? 0
    }
}
