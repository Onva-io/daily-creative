import Foundation
import Observation

@MainActor
@Observable
final class SettingsViewModel {
    var preferences: UserPreferencesModel = .defaults
    var isLoading = false
    var isSaving = false
    var errorMessage: String?
    var loadFailed = false

    private let auth: AuthSessionStore
    private let preferencesService: any PreferencesServing

    init(auth: AuthSessionStore, preferencesService: any PreferencesServing) {
        self.auth = auth
        self.preferencesService = preferencesService
    }

    var selectedTimer: TimerPreferenceOption? {
        TimerPreferenceOption.from(
            mode: preferences.rememberedTimerMode,
            seconds: preferences.rememberedTimerSeconds
        )
    }

    func load() async {
        guard let token = auth.accessToken else {
            loadFailed = false
            preferences = .defaults
            return
        }
        isLoading = true
        errorMessage = nil
        loadFailed = false
        defer { isLoading = false }
        do {
            preferences = try await preferencesService.getPreferences(accessToken: token)
        } catch {
            loadFailed = true
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    func setRememberTimer(_ enabled: Bool) async {
        preferences.rememberTimerOption = enabled
        if !enabled {
            preferences.rememberedTimerMode = nil
            preferences.rememberedTimerSeconds = nil
        } else if preferences.rememberedTimerMode == nil {
            preferences.rememberedTimerMode = TimerPreferenceOption.fiveMinutes.mode
            preferences.rememberedTimerSeconds = TimerPreferenceOption.fiveMinutes.seconds
        }
        await save()
    }

    func setTimerOption(_ option: TimerPreferenceOption) async {
        preferences.rememberTimerOption = true
        preferences.rememberedTimerMode = option.mode
        preferences.rememberedTimerSeconds = option.seconds
        await save()
    }

    func setNotificationsEnabled(_ enabled: Bool) async {
        preferences.notificationsEnabled = enabled
        if enabled && preferences.notificationTimeLocal == nil {
            preferences.notificationTimeLocal = "09:00:00"
        }
        await save()
    }

    func setAppearance(_ appearance: String) async {
        preferences.appearance = appearance
        await save()
    }

    func save() async {
        guard let token = auth.accessToken else { return }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }
        do {
            preferences = try await preferencesService.updatePreferences(
                accessToken: token,
                preferences: preferences
            )
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            await load()
        }
    }
}
