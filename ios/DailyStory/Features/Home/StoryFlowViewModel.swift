import Foundation
import Observation

@MainActor
@Observable
final class StoryFlowViewModel {
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

    private(set) var sessionViewModel: StorySessionViewModel?
    private(set) var promptWords: [String]?

    private let auth: AuthSessionStore
    private let preferencesService: any PreferencesServing
    private let guestTimerStore: any GuestTimerPreferenceStoring
    private let sessionService: any StorySessionServing
    private let draftTextStore: any DraftTextStoring
    private let submissionService: any SubmissionServing
    private let publishedStore: any PublishedSubmissionStoring
    private let analytics: any AnalyticsTracking
    private let onPublishedToday: (() -> Void)?

    private var currentSessionId: UUID?
    private var currentPrompt: DailyPromptModel?
    private var cachedAuthenticatedPreference: TimerPreferenceOption?

    init(
        auth: AuthSessionStore,
        preferencesService: any PreferencesServing,
        guestTimerStore: any GuestTimerPreferenceStoring,
        sessionService: any StorySessionServing,
        draftTextStore: any DraftTextStoring,
        submissionService: any SubmissionServing,
        publishedStore: any PublishedSubmissionStoring,
        analytics: any AnalyticsTracking,
        onPublishedToday: (() -> Void)? = nil
    ) {
        self.auth = auth
        self.preferencesService = preferencesService
        self.guestTimerStore = guestTimerStore
        self.sessionService = sessionService
        self.draftTextStore = draftTextStore
        self.submissionService = submissionService
        self.publishedStore = publishedStore
        self.analytics = analytics
        self.onPublishedToday = onPublishedToday
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

    func startWriting(prompt: DailyPromptModel) {
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
                selectedTimerOption = nil
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
        showsTimerSelection = false
        Task {
            await beginSession(
                prompt: prompt,
                option: selectedTimerOption,
                remember: rememberChoice
            )
        }
    }

    func handleTimerCompleted() {
        enterWritingPhase(eventType: "timer_completed")
    }

    func handleFinishedEarly() {
        enterWritingPhase(eventType: "finished_early")
    }

    func handleSessionEnded() {
        showsActiveSession = false
        if !showsWritingEditor {
            sessionViewModel = nil
        }
    }

    func saveDraft() {
        guard let sessionId = currentSessionId else { return }
        draftTextStore.saveDraft(draftText, forSessionId: sessionId)
        draftSavedBanner = "Draft saved."
        analytics.track(.storyDraftSaved)
        Task {
            if let token = auth.accessToken {
                _ = try? await sessionService.recordEvent(
                    accessToken: token,
                    sessionId: sessionId,
                    eventType: "draft_saved"
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
                let submission = try await submissionService.createStorySubmission(
                    accessToken: token,
                    storySessionId: sessionId,
                    body: body,
                    caption: nil,
                    idempotencyKey: UUID().uuidString
                )
                draftTextStore.deleteDraft(forSessionId: sessionId)
                lastPublishedSubmissionId = submission.id
                showsWritingEditor = false
                draftText = ""
                currentSessionId = nil
                sessionViewModel = nil
                onPublishedToday?()
                analytics.track(.storyPublished)
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
        guard let token = auth.accessToken else {
            authSheetMode = .signUp
            showsAuthSheet = true
            return
        }

        if remember {
            await persistRemembered(option)
        }

        isCreatingSession = true
        defer { isCreatingSession = false }

        do {
            let session = try await sessionService.createSession(
                accessToken: token,
                promptId: prompt.id,
                timerMode: option.mode,
                selectedTimerSeconds: option.seconds,
                idempotencyKey: UUID().uuidString
            )
            currentSessionId = session.id
            currentPrompt = prompt
            promptWords = prompt.words
            if let draft = draftTextStore.loadDraft(forSessionId: session.id) {
                draftText = draft
            }

            let model = StorySessionViewModel(
                sessionId: session.id,
                promptWords: prompt.words,
                timerMode: option.mode,
                timerSeconds: option.seconds,
                sessionService: sessionService,
                accessToken: token,
                onTimerCompleted: { [weak self] in
                    self?.handleTimerCompleted()
                },
                onFinishedEarly: { [weak self] in
                    self?.handleFinishedEarly()
                }
            )
            sessionViewModel = model
            showsActiveSession = true
            analytics.track(.storySessionStarted)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func enterWritingPhase(eventType: String) {
        _ = eventType
        showsActiveSession = false
        showsWritingEditor = true
        analytics.track(.storyWritingStarted)
        guard let token = auth.accessToken, let sessionId = currentSessionId else { return }
        Task {
            _ = try? await sessionService.recordEvent(
                accessToken: token,
                sessionId: sessionId,
                eventType: "writing_started"
            )
        }
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
