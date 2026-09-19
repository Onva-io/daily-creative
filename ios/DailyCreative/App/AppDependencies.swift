import Foundation
import Observation

@MainActor
@Observable
final class AppDependencies {
    /// The one creative type this App Store target ships.
    let module: any CreativeModule
    let environment: AppEnvironment
    let navigation: AppNavigationStore
    let auth: AuthSessionStore
    let preferencesService: any PreferencesServing
    let profileUpdater: any ProfileUpdating
    let profileRepository: any ProfileFetching
    let promptRepository: PromptRepository
    let sessionRepository: any CreativeSessionServing
    let uploadRepository: any UploadServing
    let submissionRepository: any SubmissionServing
    let socialRepository: any SocialServing
    let safetyRepository: any SafetyServing
    let accountDeleter: any AccountDeleting
    let policyService: any PolicyServing
    let directUploader: any DirectUploadTransporting
    let activeSessionStore: any ActiveSessionStoring
    let guestTimerPreferenceStore: any GuestTimerPreferenceStoring
    let draftStore: any DraftStoring
    let draftImageStore: any DraftImageStoring
    let draftTextStore: any DraftTextStoring
    let publishedSubmissionStore: any PublishedSubmissionStoring
    let cameraAuthorizer: any CameraAuthorizing
    let reminderScheduler: any ReminderScheduling
    let reminderNotificationDelegate: ReminderNotificationDelegate
    let networkMonitor: NetworkPathMonitorService
    let homeCacheStore: any HomeCacheStoring
    let appearanceStore: AppearanceStore
    let analytics: any AnalyticsTracking

    init(
        module: any CreativeModule,
        environment: AppEnvironment,
        navigation: AppNavigationStore = AppNavigationStore(),
        auth: AuthSessionStore,
        preferencesService: any PreferencesServing,
        profileUpdater: any ProfileUpdating,
        profileRepository: any ProfileFetching,
        promptRepository: PromptRepository,
        sessionRepository: any CreativeSessionServing,
        uploadRepository: any UploadServing,
        submissionRepository: any SubmissionServing,
        socialRepository: any SocialServing,
        safetyRepository: any SafetyServing,
        accountDeleter: any AccountDeleting,
        policyService: any PolicyServing,
        directUploader: any DirectUploadTransporting = URLSessionDirectUploader(),
        activeSessionStore: any ActiveSessionStoring,
        guestTimerPreferenceStore: any GuestTimerPreferenceStoring,
        draftStore: any DraftStoring,
        draftImageStore: any DraftImageStoring,
        draftTextStore: any DraftTextStoring = DraftTextStore(),
        publishedSubmissionStore: any PublishedSubmissionStoring,
        cameraAuthorizer: any CameraAuthorizing,
        reminderScheduler: any ReminderScheduling = SystemReminderScheduler(),
        reminderNotificationDelegate: ReminderNotificationDelegate? = nil,
        networkMonitor: NetworkPathMonitorService? = nil,
        homeCacheStore: any HomeCacheStoring = HomeCacheStore(),
        appearanceStore: AppearanceStore = AppearanceStore(),
        analytics: any AnalyticsTracking = AnalyticsClient.shared
    ) {
        self.module = module
        self.environment = environment
        self.navigation = navigation
        self.auth = auth
        self.preferencesService = preferencesService
        self.profileUpdater = profileUpdater
        self.profileRepository = profileRepository
        self.promptRepository = promptRepository
        self.sessionRepository = sessionRepository
        self.uploadRepository = uploadRepository
        self.submissionRepository = submissionRepository
        self.socialRepository = socialRepository
        self.safetyRepository = safetyRepository
        self.accountDeleter = accountDeleter
        self.policyService = policyService
        self.directUploader = directUploader
        self.activeSessionStore = activeSessionStore
        self.guestTimerPreferenceStore = guestTimerPreferenceStore
        self.draftStore = draftStore
        self.draftImageStore = draftImageStore
        self.draftTextStore = draftTextStore
        self.publishedSubmissionStore = publishedSubmissionStore
        self.cameraAuthorizer = cameraAuthorizer
        self.reminderScheduler = reminderScheduler
        self.reminderNotificationDelegate = reminderNotificationDelegate ?? ReminderNotificationDelegate(navigation: navigation)
        self.networkMonitor = networkMonitor ?? NetworkPathMonitorService()
        self.homeCacheStore = homeCacheStore
        self.appearanceStore = appearanceStore
        self.analytics = analytics
        self.reminderNotificationDelegate.configure(with: navigation)
    }

    var reminderSync: ReminderPreferenceSync {
        ReminderPreferenceSync(scheduler: reminderScheduler)
    }

    @MainActor
    func hydrateUserPreferences() async {
        guard let token = auth.accessToken else { return }
        do {
            var prefs = try await preferencesService.getPreferences(accessToken: token)
            let currentTimezone = TimeZone.current.identifier
            if prefs.timezone != currentTimezone {
                prefs.timezone = currentTimezone
                prefs = try await preferencesService.updatePreferences(
                    accessToken: token,
                    preferences: prefs
                )
            }
            appearanceStore.update(from: prefs)
            await reminderSync.sync(preferences: prefs)
        } catch {
            // Keep last-known appearance and reminder schedule on refresh failure.
        }
    }

    /// Dependencies for SwiftUI previews in shared code. Skips the
    /// module/Info.plist check so shared previews render in every target.
    @MainActor
    static var preview: AppDependencies {
        build(module: PreviewCreativeModule())
    }

    @MainActor
    static func live(module: any CreativeModule) -> AppDependencies {
        assert(
            module.creativeTypeID == ProductConfig.current.creativeTypeID,
            "CreativeModule '\(module.creativeTypeID)' does not match CREATIVE_TYPE_ID '\(ProductConfig.current.creativeTypeID)' in Info.plist."
        )
        return build(module: module)
    }

    @MainActor
    private static func build(module: any CreativeModule) -> AppDependencies {
        let environment = AppEnvironment.current
        let navigation = AppNavigationStore()
        let repository = MeRepository(baseURL: environment.apiBaseURL)
        let profileRepository = ProfileRepository(baseURL: environment.apiBaseURL)
        let promptRepository = PromptRepository(baseURL: environment.apiBaseURL)
        let sessionRepository = CreativeSessionRepository(baseURL: environment.apiBaseURL)
        let uploadRepository = UploadRepository(baseURL: environment.apiBaseURL)
        let submissionRepository = SubmissionRepository(baseURL: environment.apiBaseURL)
        let socialRepository = SocialRepository(baseURL: environment.apiBaseURL)
        let safetyRepository = SafetyRepository(baseURL: environment.apiBaseURL)
        let activeSessionStore = ActiveSessionStore()
        let guestTimerPreferenceStore = GuestTimerPreferenceStore()
        let draftStore = DraftStore()
        let draftImageStore = DraftImageStore()
        let draftTextStore = DraftTextStore()
        let publishedSubmissionStore = PublishedSubmissionStore()
        let cameraAuthorizer = SystemCameraAuthorizer()
        let projectID = environment.descopeProjectID

        let authService: any AuthServing
        if environment.kind.allowsMockAuthentication, DescopeConfig.isPlaceholderProjectID(projectID) {
            authService = MockAuthService()
        } else {
            if DescopeConfig.isPlaceholderProjectID(projectID) {
                preconditionFailure(
                    "DESCOPE_PROJECT_ID must be configured for \(environment.kind.rawValue) builds. Mock authentication is not allowed."
                )
            }
            authService = DescopeAuthService(projectID: projectID)
        }

        let auth = AuthSessionStore(
            authService: authService,
            meFetcher: repository,
            profileUpdater: repository,
            policyService: repository
        )
        return AppDependencies(
            module: module,
            environment: environment,
            navigation: navigation,
            auth: auth,
            preferencesService: repository,
            profileUpdater: repository,
            profileRepository: profileRepository,
            promptRepository: promptRepository,
            sessionRepository: sessionRepository,
            uploadRepository: uploadRepository,
            submissionRepository: submissionRepository,
            socialRepository: socialRepository,
            safetyRepository: safetyRepository,
            accountDeleter: repository,
            policyService: repository,
            activeSessionStore: activeSessionStore,
            guestTimerPreferenceStore: guestTimerPreferenceStore,
            draftStore: draftStore,
            draftImageStore: draftImageStore,
            draftTextStore: draftTextStore,
            publishedSubmissionStore: publishedSubmissionStore,
            cameraAuthorizer: cameraAuthorizer
        )
    }
}
