import Foundation
import Observation

/// Orchestrates the story flow: timer → writing editor → publish.
///
/// Uses the shared `TimedSessionViewModel` for the timer part and only adds
/// what is story-specific: the text editor, local text drafts and the
/// `writing_started` / `draft_saved` stage events.
@MainActor
@Observable
final class StoryFlowViewModel {
    static let writingStageEvent = "writing_started"
    static let draftSavedEvent = "draft_saved"

    var showsTimerSelection = false
    var showsActiveSession = false
    var showsWritingEditor = false
    var showsAuthSheet = false
    var authSheetMode: AuthenticationView.Mode = .signUp
    var selectedTimerOption: TimerPreferenceOption?
    var rememberChoice = false
    var isCreatingSession = false
    var isPublishing = false
    var draftText = ""
    var errorMessage: String?
    var draftSavedBanner: String?
    var lastPublishedSubmissionId: UUID?

    private(set) var sessionViewModel: TimedSessionViewModel?
    private(set) var promptWords: [String]?

    let creativeType: String
    let sessionLabels: TimedSessionLabels
    let defaultTimerOption: TimerPreferenceOption?

    private let auth: AuthSessionStore
    private let preferencesService: any PreferencesServing
    private let guestTimerStore: any GuestTimerPreferenceStoring
    private let activeSessionStore: any ActiveSessionStoring
    private let sessionService: any CreativeSessionServing
    private let draftTextStore: any DraftTextStoring
    private let submissionService: any SubmissionServing
    private let publishedStore: any PublishedSubmissionStoring
    private let dateProvider: any DateProviding
    private let analytics: any AnalyticsTracking
    private let onPublishedToday: (() -> Void)?

    private var currentSessionId: UUID?
    private var currentPrompt: DailyPromptModel?
    private var currentTimerOption: TimerPreferenceOption?
    private var cachedAuthenticatedPreference: TimerPreferenceOption?

    init(
        creativeType: String,
        sessionLabels: TimedSessionLabels,
        defaultTimerOption: TimerPreferenceOption? = nil,
        auth: AuthSessionStore,
        preferencesService: any PreferencesServing,
        guestTimerStore: any GuestTimerPreferenceStoring,
        activeSessionStore: any ActiveSessionStoring,
        sessionService: any CreativeSessionServing,
        draftTextStore: any DraftTextStoring,
        submissionService: any SubmissionServing,
        publishedStore: any PublishedSubmissionStoring,
        dateProvider: any DateProviding = SystemDateProvider(),
        analytics: any AnalyticsTracking,
        onPublishedToday: (() -> Void)? = nil
    ) {
        self.creativeType = creativeType
        self.sessionLabels = sessionLabels
        self.defaultTimerOption = defaultTimerOption
        self.auth = auth
        self.preferencesService = preferencesService
        self.guestTimerStore = guestTimerStore
        self.activeSessionStore = activeSessionStore
        self.sessionService = sessionService
        self.draftTextStore = draftTextStore
        self.submissionService = submissionService
        self.publishedStore = publishedStore
        self.dateProvider = dateProvider
        self.analytics = analytics
        self.onPublishedToday = onPublishedToday
    }

    static func make(
        dependencies: AppDependencies,
        onPublishedToday: (() -> Void)? = nil
    ) -> StoryFlowViewModel {
        StoryFlowViewModel(
            creativeType: dependencies.module.creativeTypeID,
            sessionLabels: dependencies.module.sessionLabels,
            defaultTimerOption: dependencies.module.defaultTimerOption,
            auth: dependencies.auth,
            preferencesService: dependencies.preferencesService,
            guestTimerStore: dependencies.guestTimerPreferenceStore,
            activeSessionStore: dependencies.activeSessionStore,
            sessionService: dependencies.sessionRepository,
            draftTextStore: dependencies.draftTextStore,
            submissionService: dependencies.submissionRepository,
            publishedStore: dependencies.publishedSubmissionStore,
            analytics: dependencies.analytics,
            onPublishedToday: onPublishedToday
        )
    }

    var wordCount: Int {
        draftText
            .split { $0.isWhitespace || $0.isNewline }
            .filter { !$0.isEmpty }
            .count
    }

    func prepareOnAppear() {
        Task { await refreshRememberedPreference() }
    }

    func start(prompt: DailyPromptModel) {
        guard auth.isAuthenticated else {
            authSheetMode = .signUp
            showsAuthSheet = true
            return
        }
        currentPrompt = prompt
        promptWords = prompt.words
        Task {
            await refreshRememberedPreference()
            if let remembered = rememberedTimerOption() {
                selectedTimerOption = remembered
                await beginSession(prompt: prompt, option: remembered, remember: false)
            } else {
                selectedTimerOption = defaultTimerOption
                rememberChoice = false
                showsTimerSelection = true
            }
        }
    }

    func dismissTimerSelection() {
        showsTimerSelection = false
        selectedTimerOption = nil
        rememberChoice = false
    }

    func confirmTimerSelection(prompt: DailyPromptModel) {
        guard let selectedTimerOption else { return }
        analytics.track(.timerOptionSelected, properties: ["timer_mode": selectedTimerOption.mode])
        showsTimerSelection = false
        Task {
            await beginSession(
                prompt: prompt,
                option: selectedTimerOption,
                remember: rememberChoice
            )
        }
    }

    func handleSessionEnded() {
        showsActiveSession = false
        sessionViewModel?.stopTicking()
        if !showsWritingEditor {
            sessionViewModel = nil
            currentSessionId = nil
        }
    }

    func saveDraft() {
        guard let sessionId = currentSessionId else { return }
        draftTextStore.saveDraft(draftText, forSessionId: sessionId)
        draftSavedBanner = "Draft saved."
        analytics.track(.draftSaved)
        Task {
            if let token = auth.accessToken {
                _ = try? await sessionService.postEvent(
                    accessToken: token,
                    sessionId: sessionId,
                    eventType: Self.draftSavedEvent,
                    clientOccurredAt: dateProvider.now()
                )
            }
        }
    }

    func submitStory() {
        guard let token = auth.accessToken,
              let sessionId = currentSessionId else {
            authSheetMode = .signIn
            showsAuthSheet = true
            return
        }

        let body = draftText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else {
            errorMessage = "Please write something before publishing."
            return
        }

        isPublishing = true
        Task {
            defer { isPublishing = false }
            do {
                let submission = try await submissionService.createPublication(
                    accessToken: token,
                    creativeType: creativeType,
                    sessionId: sessionId,
                    promptId: currentPrompt?.id ?? UUID(),
                    content: .story(body: body, caption: nil),
                    idempotencyKey: "story-publish-\(sessionId.uuidString)"
                )
                draftTextStore.deleteDraft(forSessionId: sessionId)
                if let prompt = currentPrompt {
                    let published = PublishedLocalSubmission(
                        id: submission.id,
                        promptId: prompt.id,
                        promptDate: prompt.promptDate,
                        timerMode: currentTimerOption?.mode ?? submission.timerMode,
                        selectedTimerSeconds: currentTimerOption?.seconds ?? submission.timerSeconds,
                        caption: submission.caption,
                        publishedAt: submission.publishedAt
                    )
                    try? publishedStore.save(published)
                }
                lastPublishedSubmissionId = submission.id
                showsWritingEditor = false
                draftText = ""
                currentSessionId = nil
                sessionViewModel = nil
                onPublishedToday?()
                analytics.track(.submissionPublished, properties: ["submission_id": submission.id.uuidString])
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    private func beginSession(
        prompt: DailyPromptModel,
        option: TimerPreferenceOption,
        remember: Bool
    ) async {
        guard let token = await auth.validAccessToken() else {
            authSheetMode = .signUp
            showsAuthSheet = true
            return
        }

        if remember {
            await persistRemembered(option)
        }

        isCreatingSession = true
        defer { isCreatingSession = false }

        let localId = UUID()
        let startedAt = dateProvider.now()
        do {
            let session = try await sessionService.createSession(
                accessToken: token,
                creativeType: creativeType,
                promptId: prompt.id,
                timerMode: option.mode,
                selectedTimerSeconds: option.seconds,
                clientTimezone: TimeZone.current.identifier,
                clientSessionId: localId.uuidString,
                clientStartedAt: startedAt,
                idempotencyKey: localId.uuidString
            )
            currentSessionId = session.id
            currentPrompt = prompt
            currentTimerOption = option
            promptWords = prompt.words
            if let draft = draftTextStore.loadDraft(forSessionId: session.id) {
                draftText = draft
            }

            let model = TimedSessionViewModel(
                creativeType: creativeType,
                labels: sessionLabels,
                prompt: prompt,
                timerOption: option,
                localSessionId: localId,
                serverSessionId: session.id,
                startedAt: startedAt,
                isGuest: false,
                postTimerStageEvent: Self.writingStageEvent,
                accessTokenProvider: { [weak self] in await self?.auth.validAccessToken() },
                sessionService: sessionService,
                activeSessionStore: activeSessionStore,
                dateProvider: dateProvider,
                analytics: analytics,
                onEnded: { [weak self] in
                    self?.handleSessionEnded()
                },
                onContinue: { [weak self] in
                    self?.enterWritingPhase()
                }
            )
            sessionViewModel = model
            showsActiveSession = true
            analytics.track(.sessionStarted, properties: ["timer_mode": option.mode])
            model.startTicking()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func enterWritingPhase() {
        sessionViewModel?.stopTicking()
        // The story flow has no session-recovery UI; the text draft is what
        // survives, keyed by server session id.
        try? activeSessionStore.clear()
        showsActiveSession = false
        showsWritingEditor = true
        analytics.track(.creationStepStarted, properties: ["step": "writing"])
    }

    private func rememberedTimerOption() -> TimerPreferenceOption? {
        if auth.isAuthenticated {
            return cachedAuthenticatedPreference
        }
        return guestTimerStore.load()
    }

    private func refreshRememberedPreference() async {
        guard auth.isAuthenticated, let token = auth.accessToken else {
            cachedAuthenticatedPreference = guestTimerStore.load()
            return
        }
        do {
            let prefs = try await preferencesService.getPreferences(accessToken: token)
            if prefs.rememberTimerOption {
                cachedAuthenticatedPreference = TimerPreferenceOption.from(
                    mode: prefs.rememberedTimerMode,
                    seconds: prefs.rememberedTimerSeconds
                )
            } else {
                cachedAuthenticatedPreference = nil
            }
        } catch {
            // Keep last-known preference.
        }
    }

    private func persistRemembered(_ option: TimerPreferenceOption) async {
        if auth.isAuthenticated, let token = auth.accessToken {
            do {
                var prefs = try await preferencesService.getPreferences(accessToken: token)
                prefs.rememberTimerOption = true
                prefs.rememberedTimerMode = option.mode
                prefs.rememberedTimerSeconds = option.seconds
                _ = try await preferencesService.updatePreferences(
                    accessToken: token,
                    preferences: prefs
                )
                cachedAuthenticatedPreference = option
            } catch {
                // Non-fatal; session can still start.
            }
        } else {
            guestTimerStore.save(option)
        }
    }
}
