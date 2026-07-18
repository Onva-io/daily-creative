import Foundation
import Observation

@Observable
final class AppDependencies {
    let environment: AppEnvironment
    let navigation: AppNavigationStore
    let auth: AuthSessionStore
    let descopeAuthService: DescopeAuthService?
    let preferencesService: any PreferencesServing
    let profileUpdater: any ProfileUpdating
    let promptRepository: PromptRepository
    let sketchSessionRepository: any SketchSessionServing
    let activeSessionStore: any ActiveSessionStoring
    let guestTimerPreferenceStore: any GuestTimerPreferenceStoring
    let draftStore: any DraftStoring
    let draftImageStore: any DraftImageStoring
    let cameraAuthorizer: any CameraAuthorizing

    init(
        environment: AppEnvironment,
        navigation: AppNavigationStore = AppNavigationStore(),
        auth: AuthSessionStore,
        descopeAuthService: DescopeAuthService? = nil,
        preferencesService: any PreferencesServing,
        profileUpdater: any ProfileUpdating,
        promptRepository: PromptRepository,
        sketchSessionRepository: any SketchSessionServing,
        activeSessionStore: any ActiveSessionStoring,
        guestTimerPreferenceStore: any GuestTimerPreferenceStoring,
        draftStore: any DraftStoring,
        draftImageStore: any DraftImageStoring,
        cameraAuthorizer: any CameraAuthorizing
    ) {
        self.environment = environment
        self.navigation = navigation
        self.auth = auth
        self.descopeAuthService = descopeAuthService
        self.preferencesService = preferencesService
        self.profileUpdater = profileUpdater
        self.promptRepository = promptRepository
        self.sketchSessionRepository = sketchSessionRepository
        self.activeSessionStore = activeSessionStore
        self.guestTimerPreferenceStore = guestTimerPreferenceStore
        self.draftStore = draftStore
        self.draftImageStore = draftImageStore
        self.cameraAuthorizer = cameraAuthorizer
    }

    @MainActor
    func makeSketchFlowViewModel() -> SketchFlowViewModel {
        SketchFlowViewModel(
            auth: auth,
            preferencesService: preferencesService,
            guestTimerStore: guestTimerPreferenceStore,
            activeSessionStore: activeSessionStore,
            sessionService: sketchSessionRepository,
            draftStore: draftStore,
            imageStore: draftImageStore,
            cameraAuthorizer: cameraAuthorizer
        )
    }

    @MainActor
    static var live: AppDependencies {
        let environment = AppEnvironment.current
        let repository = MeRepository(baseURL: environment.apiBaseURL)
        let promptRepository = PromptRepository(baseURL: environment.apiBaseURL)
        let sketchSessionRepository = SketchSessionRepository(baseURL: environment.apiBaseURL)
        let activeSessionStore = ActiveSessionStore()
        let guestTimerPreferenceStore = GuestTimerPreferenceStore()
        let draftStore = DraftStore()
        let draftImageStore = DraftImageStore()
        let cameraAuthorizer = SystemCameraAuthorizer()
        let projectID = environment.descopeProjectID

        if projectID == DescopeConfig.placeholderProjectID || projectID.isEmpty {
            let authService = MockAuthService()
            let auth = AuthSessionStore(
                authService: authService,
                meFetcher: repository,
                profileUpdater: repository
            )
            return AppDependencies(
                environment: environment,
                auth: auth,
                descopeAuthService: nil,
                preferencesService: repository,
                profileUpdater: repository,
                promptRepository: promptRepository,
                sketchSessionRepository: sketchSessionRepository,
                activeSessionStore: activeSessionStore,
                guestTimerPreferenceStore: guestTimerPreferenceStore,
                draftStore: draftStore,
                draftImageStore: draftImageStore,
                cameraAuthorizer: cameraAuthorizer
            )
        }

        let descope = DescopeAuthService(projectID: projectID)
        let auth = AuthSessionStore(
            authService: descope,
            meFetcher: repository,
            profileUpdater: repository
        )
        return AppDependencies(
            environment: environment,
            auth: auth,
            descopeAuthService: descope,
            preferencesService: repository,
            profileUpdater: repository,
            promptRepository: promptRepository,
            sketchSessionRepository: sketchSessionRepository,
            activeSessionStore: activeSessionStore,
            guestTimerPreferenceStore: guestTimerPreferenceStore,
            draftStore: draftStore,
            draftImageStore: draftImageStore,
            cameraAuthorizer: cameraAuthorizer
        )
    }
}
