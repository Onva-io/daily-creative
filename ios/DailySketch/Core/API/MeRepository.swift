import Foundation
@preconcurrency import DailySketchAPI

protocol MeFetching: Sendable {
    func fetchMe(accessToken: String) async throws -> CurrentUserProfile
}

protocol ProfileUpdating: Sendable {
    func updateMe(
        accessToken: String,
        username: String?,
        displayName: String?,
        bio: String?
    ) async throws -> CurrentUserProfile
}

protocol PreferencesServing: Sendable {
    func getPreferences(accessToken: String) async throws -> UserPreferencesModel
    func updatePreferences(
        accessToken: String,
        preferences: UserPreferencesModel
    ) async throws -> UserPreferencesModel
}

struct MeRepository: MeFetching, ProfileUpdating, PreferencesServing {
    let baseURL: URL

    func fetchMe(accessToken: String) async throws -> CurrentUserProfile {
        configureClient(accessToken: accessToken)
        do {
            let user = try await MeAPI.getMe()
            return mapProfile(user)
        } catch {
            throw mapAPIError(error)
        }
    }

    func updateMe(
        accessToken: String,
        username: String?,
        displayName: String?,
        bio: String?
    ) async throws -> CurrentUserProfile {
        configureClient(accessToken: accessToken)
        do {
            let request = UpdateMeRequest(username: username, displayName: displayName, bio: bio)
            let user = try await MeAPI.updateMe(updateMeRequest: request)
            return mapProfile(user)
        } catch {
            throw mapAPIError(error)
        }
    }

    func getPreferences(accessToken: String) async throws -> UserPreferencesModel {
        configureClient(accessToken: accessToken)
        do {
            let prefs = try await MeAPI.getMyPreferences()
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
            let prefs = try await MeAPI.updateMyPreferences(preferencesUpdate: request)
            return mapPreferences(prefs)
        } catch {
            throw mapAPIError(error)
        }
    }

    private func configureClient(accessToken: String) {
        var base = baseURL.absoluteString
        if base.hasSuffix("/") {
            base.removeLast()
        }
        DailySketchAPIAPI.basePath = base
        DailySketchAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"
        DailySketchAPITokenBridge.setBearerToken(accessToken)
    }

    private func mapProfile(_ user: CurrentUser) -> CurrentUserProfile {
        CurrentUserProfile(
            id: user.id,
            username: user.username,
            displayName: user.displayName,
            profileCompleted: user.profileCompleted,
            status: user.status.rawValue
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
final class RecordingMeFetcher: MeFetching, ProfileUpdating, PreferencesServing, @unchecked Sendable {
    private(set) var lastAccessToken: String?
    var profile: CurrentUserProfile
    var preferences: UserPreferencesModel = .defaults
    var error: Error?
    var updateError: Error?

    init(profile: CurrentUserProfile) {
        self.profile = profile
    }

    func fetchMe(accessToken: String) async throws -> CurrentUserProfile {
        lastAccessToken = accessToken
        DailySketchAPITokenBridge.setBearerToken(accessToken)
        if let error {
            throw error
        }
        return profile
    }

    func updateMe(
        accessToken: String,
        username: String?,
        displayName: String?,
        bio: String?
    ) async throws -> CurrentUserProfile {
        lastAccessToken = accessToken
        if let updateError {
            throw updateError
        }
        profile = CurrentUserProfile(
            id: profile.id,
            username: username ?? profile.username,
            displayName: displayName ?? profile.displayName,
            profileCompleted: username != nil,
            status: username != nil ? "active" : profile.status
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
}
