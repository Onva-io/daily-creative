import Foundation
@preconcurrency import DailyCreativeAPI

protocol MeFetching: Sendable {
    func fetchMe(accessToken: String) async throws -> CurrentUserProfile
}

protocol ProfileUpdating: Sendable {
    func updateMe(
        accessToken: String,
        username: String?,
        displayName: String?,
        bio: String?,
        avatarUploadId: UUID?
    ) async throws -> CurrentUserProfile
}

protocol PreferencesServing: Sendable {
    func getPreferences(accessToken: String) async throws -> UserPreferencesModel
    func updatePreferences(
        accessToken: String,
        preferences: UserPreferencesModel
    ) async throws -> UserPreferencesModel
}

protocol AccountDeleting: Sendable {
    func deleteAccount(accessToken: String, idempotencyKey: String?) async throws
}

protocol PolicyServing: Sendable {
    func fetchCurrentPolicies() async throws -> [PolicyDocumentSummary]
    func acceptPolicies(
        accessToken: String,
        documents: [(kind: String, version: String)],
        appVersion: String?,
        platform: String?,
        locale: String?
    ) async throws
    func setDateOfBirth(accessToken: String, dateOfBirth: Date) async throws -> CurrentUserProfile
}

struct MeRepository: MeFetching, ProfileUpdating, PreferencesServing, AccountDeleting, PolicyServing {
    let baseURL: URL

    func fetchMe(accessToken: String) async throws -> CurrentUserProfile {
        configureClient(accessToken: accessToken)
        do {
            let user = try await MeAPI.getMe(
                creativeType: FeedMapping.apiCreativeType()
            )
            return mapProfile(user)
        } catch {
            throw mapAPIError(error)
        }
    }

    func deleteAccount(accessToken: String, idempotencyKey: String?) async throws {
        configureClient(accessToken: accessToken)
        do {
            _ = try await MeAPI.deleteMe(idempotencyKey: idempotencyKey)
        } catch {
            throw mapAPIError(error)
        }
    }

    func updateMe(
        accessToken: String,
        username: String?,
        displayName: String?,
        bio: String?,
        avatarUploadId: UUID?
    ) async throws -> CurrentUserProfile {
        configureClient(accessToken: accessToken)
        do {
            let request = UpdateMeRequest(
                username: username,
                displayName: displayName,
                bio: bio,
                avatarUploadId: avatarUploadId
            )
            let user = try await MeAPI.updateMe(
                creativeType: FeedMapping.apiCreativeType(),
                updateMeRequest: request
            )
            return mapProfile(user)
        } catch {
            throw mapAPIError(error)
        }
    }

    func getPreferences(accessToken: String) async throws -> UserPreferencesModel {
        configureClient(accessToken: accessToken)
        do {
            let prefs = try await MeAPI.getMyPreferences(
                creativeType: FeedMapping.apiCreativeType()
            )
            return mapPreferences(prefs)
        } catch {
            throw mapAPIError(error)
        }
    }

    func updatePreferences(
        accessToken: String,
        preferences: UserPreferencesModel
    ) async throws -> UserPreferencesModel {
        configureClient(accessToken: accessToken)
        do {
            let mode: TimerMode? = preferences.rememberedTimerMode.flatMap { TimerMode(rawValue: $0) }
            let appearance = AppearancePreference(rawValue: preferences.appearance) ?? .system
            let request = PreferencesUpdate(
                notificationsEnabled: preferences.notificationsEnabled,
                notificationTimeLocal: preferences.notificationTimeLocal,
                timezone: preferences.timezone,
                rememberTimerOption: preferences.rememberTimerOption,
                rememberedTimerMode: mode,
                rememberedTimerSeconds: preferences.rememberedTimerSeconds,
                appearance: appearance
            )
            let prefs = try await MeAPI.updateMyPreferences(
                creativeType: FeedMapping.apiCreativeType(),
                preferencesUpdate: request
            )
            return mapPreferences(prefs)
        } catch {
            throw mapAPIError(error)
        }
    }

    func fetchCurrentPolicies() async throws -> [PolicyDocumentSummary] {
        configureClientUnauthenticated()
        do {
            let response = try await PoliciesAPI.getCurrentPolicies()
            return response.documents.map(mapDocument)
        } catch {
            throw mapAPIError(error)
        }
    }

    func acceptPolicies(
        accessToken: String,
        documents: [(kind: String, version: String)],
        appVersion: String?,
        platform: String?,
        locale: String?
    ) async throws {
        configureClient(accessToken: accessToken)
        do {
            let items = documents.compactMap { item -> AcceptPolicyItem? in
                guard let kind = PolicyKind(rawValue: item.kind) else { return nil }
                return AcceptPolicyItem(kind: kind, version: item.version)
            }
            let request = AcceptPoliciesRequest(
                documents: items,
                appVersion: appVersion,
                platform: platform,
                locale: locale
            )
            _ = try await PoliciesAPI.acceptPolicies(acceptPoliciesRequest: request)
        } catch {
            throw mapAPIError(error)
        }
    }

    func setDateOfBirth(accessToken: String, dateOfBirth: Date) async throws -> CurrentUserProfile {
        configureClient(accessToken: accessToken)
        do {
            let formatter = DateFormatter()
            formatter.calendar = Calendar(identifier: .gregorian)
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.timeZone = TimeZone(secondsFromGMT: 0)
            formatter.dateFormat = "yyyy-MM-dd"
            let request = SetDateOfBirthRequest(dateOfBirth: formatter.string(from: dateOfBirth))
            let user = try await PoliciesAPI.setDateOfBirth(
                creativeType: FeedMapping.apiCreativeType(),
                setDateOfBirthRequest: request
            )
            return mapProfile(user)
        } catch {
            throw mapAPIError(error)
        }
    }

    private func configureClient(accessToken: String) {
        configureClientUnauthenticated()
        DailyCreativeAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"
        DailyCreativeAPITokenBridge.setBearerToken(accessToken)
    }

    private func configureClientUnauthenticated() {
        var base = baseURL.absoluteString
        if base.hasSuffix("/") {
            base.removeLast()
        }
        DailyCreativeAPIAPI.basePath = base
    }

    private func mapProfile(_ user: CurrentUser) -> CurrentUserProfile {
        CurrentUserProfile(
            id: user.id,
            username: user.username,
            displayName: user.displayName,
            profileCompleted: user.profileCompleted,
            status: user.status.rawValue,
            avatarURL: user.avatarUrl.flatMap(URL.init(string:)),
            dateOfBirthSet: user.dateOfBirthSet,
            consent: user.consent.map(mapConsent)
        )
    }

    private func mapConsent(_ consent: ConsentState) -> ConsentSnapshot {
        ConsentSnapshot(
            consentRequired: consent.consentRequired,
            outstandingKinds: consent.outstandingKinds.map(\.rawValue),
            ageRequired: consent.ageRequired,
            minimumAge: consent.minimumAge,
            currentDocuments: consent.currentDocuments.map(mapDocument)
        )
    }

    private func mapDocument(_ document: PolicyDocument) -> PolicyDocumentSummary {
        PolicyDocumentSummary(
            id: document.id,
            kind: document.kind.rawValue,
            version: document.version,
            title: document.title,
            bodyMarkdown: document.bodyMarkdown,
            minimumAge: document.minimumAge,
            isSignificantChange: document.isSignificantChange,
            changeSummary: document.changeSummary
        )
    }

    private func mapPreferences(_ prefs: PreferencesSummary) -> UserPreferencesModel {
        UserPreferencesModel(
            notificationsEnabled: prefs.notificationsEnabled,
            notificationTimeLocal: prefs.notificationTimeLocal,
            timezone: prefs.timezone,
            rememberTimerOption: prefs.rememberTimerOption,
            rememberedTimerMode: prefs.rememberedTimerMode?.rawValue,
            rememberedTimerSeconds: prefs.rememberedTimerSeconds,
            appearance: prefs.appearance.rawValue
        )
    }

    private func mapAPIError(_ error: Error) -> Error {
        if let errorResponse = error as? ErrorResponse {
            switch errorResponse {
            case .error(let code, let data, _, _):
                if code == 401 {
                    return ProfileAPIError.sessionExpired
                }
                if let data,
                   let envelope = try? JSONDecoder().decode(APIErrorEnvelope.self, from: data) {
                    switch envelope.error.code {
                    case "username_taken":
                        return ProfileAPIError.usernameTaken
                    case "username_invalid":
                        return ProfileAPIError.usernameInvalid
                    case "username_reserved":
                        return ProfileAPIError.usernameReserved
                    case "invalid_timer_preference":
                        return ProfileAPIError.invalidTimerPreference
                    case "under_minimum_age":
                        return ProfileAPIError.underMinimumAge(envelope.error.message)
                    case "policy_version_stale":
                        return ProfileAPIError.policyVersionStale
                    case "consent_required":
                        return ProfileAPIError.consentRequired
                    case "content_rejected":
                        return ProfileAPIError.contentRejected(envelope.error.message)
                    default:
                        return ProfileAPIError.underlying(envelope.error.message)
                    }
                }
            }
        }
        return ProfileAPIError.underlying(error.localizedDescription)
    }
}

private struct APIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}

/// Test double that records the bearer token used for authenticated requests.
final class RecordingMeFetcher: MeFetching, ProfileUpdating, PreferencesServing, PolicyServing, @unchecked Sendable {
    private(set) var lastAccessToken: String?
    var profile: CurrentUserProfile
    var preferences: UserPreferencesModel = .defaults
    var policies: [PolicyDocumentSummary] = []
    var error: Error?
    var updateError: Error?

    init(profile: CurrentUserProfile) {
        self.profile = profile
    }

    func fetchMe(accessToken: String) async throws -> CurrentUserProfile {
        lastAccessToken = accessToken
        DailyCreativeAPITokenBridge.setBearerToken(accessToken)
        if let error {
            throw error
        }
        return profile
    }

    func updateMe(
        accessToken: String,
        username: String?,
        displayName: String?,
        bio: String?,
        avatarUploadId: UUID?
    ) async throws -> CurrentUserProfile {
        lastAccessToken = accessToken
        if let updateError {
            throw updateError
        }
        profile = CurrentUserProfile(
            id: profile.id,
            username: username ?? profile.username,
            displayName: displayName ?? profile.displayName,
            profileCompleted: username != nil || profile.profileCompleted,
            status: username != nil ? "active" : profile.status,
            avatarURL: profile.avatarURL,
            dateOfBirthSet: profile.dateOfBirthSet,
            consent: profile.consent
        )
        return profile
    }

    func getPreferences(accessToken: String) async throws -> UserPreferencesModel {
        lastAccessToken = accessToken
        if let error {
            throw error
        }
        return preferences
    }

    func updatePreferences(
        accessToken: String,
        preferences: UserPreferencesModel
    ) async throws -> UserPreferencesModel {
        lastAccessToken = accessToken
        if let updateError {
            throw updateError
        }
        self.preferences = preferences
        return preferences
    }

    func fetchCurrentPolicies() async throws -> [PolicyDocumentSummary] {
        if let error {
            throw error
        }
        return policies
    }

    func acceptPolicies(
        accessToken: String,
        documents: [(kind: String, version: String)],
        appVersion: String?,
        platform: String?,
        locale: String?
    ) async throws {
        lastAccessToken = accessToken
        _ = (documents, appVersion, platform, locale)
        if let updateError {
            throw updateError
        }
        if var consent = profile.consent {
            consent = ConsentSnapshot(
                consentRequired: false,
                outstandingKinds: [],
                ageRequired: consent.ageRequired,
                minimumAge: consent.minimumAge,
                currentDocuments: consent.currentDocuments
            )
            profile = CurrentUserProfile(
                id: profile.id,
                username: profile.username,
                displayName: profile.displayName,
                profileCompleted: profile.profileCompleted,
                status: profile.status,
                avatarURL: profile.avatarURL,
                dateOfBirthSet: profile.dateOfBirthSet,
                consent: consent
            )
        }
    }

    func setDateOfBirth(accessToken: String, dateOfBirth: Date) async throws -> CurrentUserProfile {
        lastAccessToken = accessToken
        _ = dateOfBirth
        if let updateError {
            throw updateError
        }
        let consent = profile.consent.map {
            ConsentSnapshot(
                consentRequired: !$0.outstandingKinds.isEmpty,
                outstandingKinds: $0.outstandingKinds,
                ageRequired: false,
                minimumAge: $0.minimumAge,
                currentDocuments: $0.currentDocuments
            )
        }
        profile = CurrentUserProfile(
            id: profile.id,
            username: profile.username,
            displayName: profile.displayName,
            profileCompleted: profile.profileCompleted,
            status: profile.status,
            avatarURL: profile.avatarURL,
            dateOfBirthSet: true,
            consent: consent
        )
        return profile
    }
}
