import Foundation

enum AuthState: Equatable, Sendable {
    case guest
    case authenticating
    case authenticated(session: AuthSession)
    case failed(message: String)
}

struct AuthSession: Equatable, Sendable {
    let accessToken: String
    let subject: String
    let displayName: String?
}

struct PolicyDocumentSummary: Equatable, Sendable, Identifiable {
    let id: UUID
    let kind: String
    let version: String
    let title: String
    let bodyMarkdown: String
    let minimumAge: Int
    let isSignificantChange: Bool
    let changeSummary: String?
}

struct ConsentSnapshot: Equatable, Sendable {
    let consentRequired: Bool
    let outstandingKinds: [String]
    let ageRequired: Bool
    let minimumAge: Int
    let currentDocuments: [PolicyDocumentSummary]

    static let empty = ConsentSnapshot(
        consentRequired: false,
        outstandingKinds: [],
        ageRequired: false,
        minimumAge: 13,
        currentDocuments: []
    )
}

struct CurrentUserProfile: Equatable, Sendable {
    let id: UUID
    let username: String?
    let displayName: String
    let profileCompleted: Bool
    let status: String
    let avatarURL: URL?
    let dateOfBirthSet: Bool
    let consent: ConsentSnapshot?

    init(
        id: UUID,
        username: String?,
        displayName: String,
        profileCompleted: Bool,
        status: String,
        avatarURL: URL? = nil,
        dateOfBirthSet: Bool = false,
        consent: ConsentSnapshot? = nil
    ) {
        self.id = id
        self.username = username
        self.displayName = displayName
        self.profileCompleted = profileCompleted
        self.status = status
        self.avatarURL = avatarURL
        self.dateOfBirthSet = dateOfBirthSet
        self.consent = consent
    }
}
