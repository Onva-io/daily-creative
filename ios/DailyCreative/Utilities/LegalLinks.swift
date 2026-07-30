import Foundation

enum LegalLinks {
    static var support: URL? { url(for: "SUPPORT_URL") }
    static var privacy: URL? { url(for: "PRIVACY_URL") }
    static var terms: URL? { url(for: "TERMS_URL") }
    static var communityGuidelines: URL? { url(for: "COMMUNITY_GUIDELINES_URL") }

    static var supportEmail: String? {
        guard let raw = Bundle.main.object(forInfoDictionaryKey: "SUPPORT_EMAIL") as? String else {
            return nil
        }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    static var supportMailto: URL? {
        guard let email = supportEmail else { return nil }
        return URL(string: "mailto:\(email)")
    }

    private static func url(for key: String) -> URL? {
        guard let raw = Bundle.main.object(forInfoDictionaryKey: key) as? String else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed)
    }
}
