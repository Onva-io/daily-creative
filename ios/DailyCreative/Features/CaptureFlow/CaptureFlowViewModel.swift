import Foundation
import Observation
import UIKit

/// Orchestrates the timer → capture → review → publish flow shared by every
/// creative type that produces an image (sketch, photo).
///
/// The creative type is injected: it decides the API discriminator, the
/// timer screen copy, the default timer option and the stage event posted when
/// the timer ends. Nothing in here branches on the type.
@MainActor
@Observable
final class CaptureFlowViewModel {
    /// Server event the sketch/photo types accept once the timer part is over.
    static let captureStageEvent = "photo_step_reached"

    var showsTimerSelection = false
    var showsActiveSession = false
    var showsCaptureSource = false
    var showsReviewSubmission = false
    var showsSaveYourCreativity = false
    var showsAuthSheet = false
    var authSheetMode: AuthenticationView.Mode = .signUp
    var showsRecoveryBanner = false
    var isCreatingSession = false
    var selectedTimerOption: TimerPreferenceOption?
    var rememberChoice = false
    var changeTimerHintVisible = false
    var syncBannerMessage: String?
    var captureValidationMessage: String?
    var draftSavedBanner: String?
    var needsProfileCompletionPresentation = false
    var lastPublishedSubmissionId: UUID?

    private(set) var sessionViewModel: TimedSessionViewModel?
    private(set) var reviewViewModel: ReviewSubmissionViewModel?
    private(set) var recoverableSnapshot: ActiveSessionSnapshot?
    private(set) var recoverableDraft: LocalDraft?
    private(set) var recoverableDraftThumbnail: UIImage?

    let creativeType: String
    let sessionLabels: TimedSessionLabels
    let defaultTimerOption: TimerPreferenceOption?
    let plugin: any CaptureContentPlugin

    private let auth: AuthSessionStore
    private let preferencesService: any PreferencesServing
    private let guestTimerStore: any GuestTimerPreferenceStoring
    private let activeSessionStore: any ActiveSessionStoring
    private let sessionService: any CreativeSessionServing
    private let draftStore: any DraftStoring
    private let imageStore: any DraftImageStoring
    private let cameraAuthorizer: any CameraAuthorizing
    private let uploadService: (any UploadServing)?
    private let submissionService: (any SubmissionServing)?
    private let directUploader: (any DirectUploadTransporting)?
    private let publishedStore: (any PublishedSubmissionStoring)?
    private let dateProvider: any DateProviding
    private let analytics: (any AnalyticsTracking)?
    private let onPublishedToday: (() -> Void)?
    private var cachedAuthenticatedPreference: TimerPreferenceOption?
    private var replacingImageInReview = false

    var cameraAuthorizerForCapture: any CameraAuthorizing { cameraAuthorizer }

    init(
        creativeType: String,
        sessionLabels: TimedSessionLabels,
        defaultTimerOption: TimerPreferenceOption? = nil,
        plugin: any CaptureContentPlugin = SketchCapturePlugin(),
        auth: AuthSessionStore,
        preferencesService: any PreferencesServing,
        guestTimerStore: any GuestTimerPreferenceStoring,
        activeSessionStore: any ActiveSessionStoring,
        sessionService: any CreativeSessionServing,
        draftStore: any DraftStoring,
        imageStore: any DraftImageStoring,
        cameraAuthorizer: any CameraAuthorizing,
        uploadService: (any UploadServing)? = nil,
        submissionService: (any SubmissionServing)? = nil,
        directUploader: (any DirectUploadTransporting)? = nil,
        publishedStore: (any PublishedSubmissionStoring)? = nil,
        dateProvider: any DateProviding = SystemDateProvider(),
        analytics: (any AnalyticsTracking)? = nil,
        onPublishedToday: (() -> Void)? = nil
    ) {
        self.creativeType = creativeType
        self.sessionLabels = sessionLabels
        self.defaultTimerOption = defaultTimerOption
        self.plugin = plugin
        self.auth = auth
        self.preferencesService = preferencesService
        self.guestTimerStore = guestTimerStore
        self.activeSessionStore = activeSessionStore
        self.sessionService = sessionService
        self.draftStore = draftStore
        self.imageStore = imageStore
        self.cameraAuthorizer = cameraAuthorizer
        self.uploadService = uploadService
        self.submissionService = submissionService
        self.directUploader = directUploader
        self.publishedStore = publishedStore
        self.dateProvider = dateProvider
        self.analytics = analytics
        self.onPublishedToday = onPublishedToday
    }

    func prepareOnAppear() {
        refreshRecoveryState()
        refreshDraftState()
        Task { await refreshRememberedPreference() }
    }

    func start(prompt: DailyPromptModel) {
        Task {
            await refreshRememberedPreference()
            if let remembered = rememberedTimerOption() {
                changeTimerHintVisible = true
                await beginSession(prompt: prompt, option: remembered, remember: false)
            } else {
                selectedTimerOption = defaultTimerOption
                rememberChoice = false
                changeTimerHintVisible = false
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
        analytics?.track(
            .timerOptionSelected,
            properties: ["timer_mode": selectedTimerOption.mode]
        )
        showsTimerSelection = false
        Task {
            await beginSession(
                prompt: prompt,
                option: selectedTimerOption,
                remember: rememberChoice
            )
        }
    }

    func changeTimerNextTime() {
        if auth.isAuthenticated {
            Task { await clearAuthenticatedRememberedTimer() }
        } else {
            guestTimerStore.clear()
        }
        changeTimerHintVisible = false
        cachedAuthenticatedPreference = nil
    }

    func resumeRecoverableSession(promptLookup: (UUID) -> DailyPromptModel?) {
        guard let snapshot = recoverableSnapshot else { return }
        guard let option = TimerPreferenceOption.from(
            mode: snapshot.timerMode,
            seconds: snapshot.selectedTimerSeconds
        ) else {
            discardRecoverableSession()
            return
        }

        let prompt = promptLookup(snapshot.promptId) ?? DailyPromptModel(
            id: snapshot.promptId,
            promptDate: dateProvider.now(),
            word1: snapshot.promptWords[safe: 0] ?? "",
            word2: snapshot.promptWords[safe: 1] ?? "",
            word3: snapshot.promptWords[safe: 2] ?? "",
            status: "published",
            publishedAt: nil
        )

        let model = makeSessionViewModel(
            prompt: prompt,
            option: option,
            localSessionId: snapshot.id,
            serverSessionId: snapshot.serverSessionId,
            startedAt: snapshot.startedAt,
            pausedAt: snapshot.pausedAt,
            pausedTotalSeconds: snapshot.pausedTotalSeconds,
            lifecycle: snapshot.lifecycle,
            syncPending: snapshot.syncPending,
            isGuest: snapshot.isGuest
        )
        sessionViewModel = model
        showsActiveSession = true
        showsRecoveryBanner = false
        model.startTicking()
    }

    func discardRecoverableSession() {
        if let snapshot = recoverableSnapshot,
           let serverId = snapshot.serverSessionId,
           let token = auth.accessToken {
            Task {
                _ = try? await sessionService.abandonSession(
                    accessToken: token,
                    sessionId: serverId
                )
            }
        }
        try? activeSessionStore.clear()
        recoverableSnapshot = nil
        showsRecoveryBanner = false
    }

    func handleSessionEnded() {
        showsActiveSession = false
        sessionViewModel?.stopTicking()
        if !showsCaptureSource, !showsReviewSubmission {
            sessionViewModel = nil
        }
        refreshRecoveryState()
    }

    func dismissCaptureSource() {
        showsCaptureSource = false
        replacingImageInReview = false
        if reviewViewModel != nil {
            showsReviewSubmission = true
        } else if sessionViewModel != nil {
            showsActiveSession = true
        }
    }

    func handleCapturedImageData(_ data: Data) {
        handleCapturedImage(CapturedImage(jpegData: data, originalData: nil, source: .library))
    }

    func handleCapturedImage(_ captured: CapturedImage) {
        captureValidationMessage = nil
        if replacingImageInReview, let reviewViewModel {
            do {
                try reviewViewModel.replaceImage(with: captured)
                replacingImageInReview = false
                showsCaptureSource = false
                showsReviewSubmission = true
            } catch {
                captureValidationMessage = error.localizedDescription
            }
            return
        }

        guard let session = sessionViewModel else { return }
        do {
            let draft = try createDraft(from: session, imageData: captured.jpegData)
            try activeSessionStore.clear()
            showsActiveSession = false
            showsCaptureSource = false
            sessionViewModel?.stopTicking()
            sessionViewModel = nil
            presentReview(for: draft, imageData: captured.jpegData, captured: captured)
            analytics?.track(.photoCapturedOrSelected)
            refreshRecoveryState()
            refreshDraftState()
        } catch {
            captureValidationMessage = error.localizedDescription
        }
    }

    func handleCaptureValidationError(_ message: String) {
        captureValidationMessage = message
    }

    func handleReviewOutcome(_ outcome: ReviewSubmissionOutcome) {
        switch outcome {
        case .savedToDrafts, .continueLater:
            draftSavedBanner = "Draft saved."
            showsReviewSubmission = false
            showsSaveYourCreativity = false
            showsAuthSheet = false
            reviewViewModel = nil
            refreshDraftState()
        case .needsAuthentication:
            showsSaveYourCreativity = true
        case .needsProfileCompletion:
            needsProfileCompletionPresentation = true
            showsReviewSubmission = true
        case .published(let submission):
            let draftId = reviewViewModel?.draft.id
            if let draftId {
                deleteDraftAfterPublication(id: draftId)
            }
            lastPublishedSubmissionId = submission.id
            draftSavedBanner = "Published to the community."
            showsReviewSubmission = false
            showsSaveYourCreativity = false
            showsAuthSheet = false
            reviewViewModel = nil
            refreshDraftState()
            onPublishedToday?()
        }
    }

    func acknowledgeProfileCompletionPresentation() {
        needsProfileCompletionPresentation = false
    }

    func continueLaterFromCreativity() {
        do {
            try reviewViewModel?.continueLaterFromAuthCheckpoint()
        } catch {
            // Fall through: still dismiss so the guest is not trapped.
            syncBannerMessage = "Couldn’t update Draft metadata."
            showsSaveYourCreativity = false
            showsReviewSubmission = false
            reviewViewModel = nil
            refreshDraftState()
            return
        }
        // onFinished(.continueLater) already clears presentation via handleReviewOutcome.
        if showsSaveYourCreativity || showsReviewSubmission {
            showsSaveYourCreativity = false
            showsReviewSubmission = false
            reviewViewModel = nil
            draftSavedBanner = "Draft saved. Continue when you’re ready."
            refreshDraftState()
        }
    }

    func presentCreateAccountFromCreativity() {
        authSheetMode = .signUp
        showsAuthSheet = true
    }

    func presentSignInFromCreativity() {
        authSheetMode = .signIn
        showsAuthSheet = true
    }

    func handleAuthenticationCompleted() {
        guard auth.isAuthenticated else { return }
        showsAuthSheet = false
        showsSaveYourCreativity = false
        reviewViewModel?.markAuthenticated()
        showsReviewSubmission = true
        if auth.needsProfileCompletion {
            needsProfileCompletionPresentation = true
            return
        }
        resumePendingPublishIfNeeded()
    }

    func resumePendingPublishIfNeeded() {
        if reviewViewModel?.draft.pendingPublication == true {
            reviewViewModel?.retryPublish()
        }
    }

    func reopenDraft(_ draft: LocalDraft? = nil) {
        let target = draft ?? recoverableDraft
        guard let target else { return }
        do {
            let data = try imageStore.readData(fileName: target.imageFileName)
            // Present Review only; auth/profile resume uses resumePendingPublishIfNeeded().
            presentReview(for: target, imageData: data)
        } catch {
            syncBannerMessage = "Couldn’t open that Draft."
        }
    }

    func discardDraft(_ draft: LocalDraft? = nil) {
        let target = draft ?? recoverableDraft
        guard let target else { return }
        try? draftStore.delete(id: target.id)
        try? imageStore.delete(fileName: target.imageFileName)
        if reviewViewModel?.draft.id == target.id {
            showsReviewSubmission = false
            showsSaveYourCreativity = false
            reviewViewModel = nil
        }
        refreshDraftState()
    }

    /// Hook for Phase 7: delete the local Draft only after confirmed publication.
    func deleteDraftAfterPublication(id: UUID) {
        guard let drafts = try? draftStore.list(),
              let draft = drafts.first(where: { $0.id == id }) else {
            return
        }
        try? draftStore.delete(id: id)
        try? imageStore.delete(fileName: draft.imageFileName)
        refreshDraftState()
    }

    private func presentReview(for draft: LocalDraft, imageData: Data, captured: CapturedImage? = nil) {
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: imageData,
            creativeType: creativeType,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: uploadService,
            submissionService: submissionService,
            sessionService: sessionService,
            extras: plugin.makeExtrasController(draft: draft, captured: captured),
            directUploader: directUploader,
            publishedStore: publishedStore,
            accessTokenProvider: { [weak self] in await self?.auth.validAccessToken() },
            isAuthenticated: { [weak self] in self?.auth.isAuthenticated ?? false },
            canPublish: { [weak self] in
                guard let self else { return false }
                return self.auth.requireCompleteProfileForPublishing()
            },
            dateProvider: dateProvider,
            analytics: analytics,
            onFinished: { [weak self] outcome in
                self?.handleReviewOutcome(outcome)
            },
            onReplaceRequested: { [weak self] in
                self?.beginReplaceImage()
            }
        )
        reviewViewModel = model
        showsReviewSubmission = true
    }

    private func beginReplaceImage() {
        replacingImageInReview = true
        showsCaptureSource = true
        showsReviewSubmission = false
    }

    private func createDraft(from session: TimedSessionViewModel, imageData: Data) throws -> LocalDraft {
        let fileName = try imageStore.write(imageData)
        let now = dateProvider.now()
        let draft = LocalDraft(
            id: UUID(),
            localSessionId: session.localSessionId,
            serverSessionId: session.serverSessionId,
            creativeType: creativeType,
            promptId: session.promptId,
            promptWords: session.promptWords,
            promptAccessibilityLabel: session.promptAccessibilityLabel,
            promptDate: session.promptDate,
            timerMode: session.timerOption.mode,
            selectedTimerSeconds: session.timerOption.seconds,
            sessionStartedAt: session.sessionStartedAt,
            imageFileName: fileName,
            caption: nil,
            createdAt: now,
            updatedAt: now,
            pendingAuthentication: !auth.isAuthenticated,
            pendingPublication: false
        )
        try draftStore.save(draft)
        return draft
    }

    private func beginSession(
        prompt: DailyPromptModel,
        option: TimerPreferenceOption,
        remember: Bool
    ) async {
        if remember {
            await persistRemembered(option)
        }

        let localId = UUID()
        let isGuest = !auth.isAuthenticated
        let startedAt = dateProvider.now()
        isCreatingSession = true
        defer { isCreatingSession = false }

        let model = makeSessionViewModel(
            prompt: prompt,
            option: option,
            localSessionId: localId,
            serverSessionId: nil,
            startedAt: startedAt,
            pausedAt: nil,
            pausedTotalSeconds: 0,
            lifecycle: .active,
            syncPending: false,
            isGuest: isGuest
        )
        sessionViewModel = model
        showsActiveSession = true
        analytics?.track(.sessionStarted, properties: ["timer_mode": option.mode])
        model.startTicking()

        guard !isGuest else { return }
        guard let token = await auth.validAccessToken() else { return }

        do {
            let created = try await sessionService.createSession(
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
            model.attachServerSessionId(created.id)
            syncBannerMessage = nil
        } catch {
            model.markSyncPending(error.localizedDescription)
            syncBannerMessage = "Session sync pending. You can keep going."
        }
    }

    private func makeSessionViewModel(
        prompt: DailyPromptModel,
        option: TimerPreferenceOption,
        localSessionId: UUID,
        serverSessionId: UUID?,
        startedAt: Date,
        pausedAt: Date?,
        pausedTotalSeconds: Int,
        lifecycle: ActiveSessionLifecycle,
        syncPending: Bool,
        isGuest: Bool
    ) -> TimedSessionViewModel {
        TimedSessionViewModel(
            creativeType: creativeType,
            labels: sessionLabels,
            prompt: prompt,
            timerOption: option,
            localSessionId: localSessionId,
            serverSessionId: serverSessionId,
            startedAt: startedAt,
            pausedAt: pausedAt,
            pausedTotalSeconds: pausedTotalSeconds,
            lifecycle: lifecycle,
            syncPending: syncPending,
            isGuest: isGuest,
            postTimerStageEvent: Self.captureStageEvent,
            accessTokenProvider: { [weak self] in await self?.auth.validAccessToken() },
            sessionService: sessionService,
            activeSessionStore: activeSessionStore,
            dateProvider: dateProvider,
            analytics: analytics,
            onEnded: { [weak self] in
                self?.handleSessionEnded()
            },
            onContinue: { [weak self] in
                self?.showsCaptureSource = true
                self?.showsActiveSession = false
            }
        )
    }

    private func rememberedTimerOption() -> TimerPreferenceOption? {
        if auth.isAuthenticated {
            return cachedAuthenticatedPreference
        }
        return guestTimerStore.load()
    }

    private func refreshRememberedPreference() async {
        if auth.isAuthenticated, let token = auth.accessToken {
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
                // Keep last known cached preference.
            }
        }
    }

    private func persistRemembered(_ option: TimerPreferenceOption) async {
        if auth.isAuthenticated, let token = auth.accessToken {
            var prefs = UserPreferencesModel.defaults
            do {
                prefs = try await preferencesService.getPreferences(accessToken: token)
            } catch {
                // Fall through with defaults and still attempt write.
            }
            prefs.rememberTimerOption = true
            prefs.rememberedTimerMode = option.mode
            prefs.rememberedTimerSeconds = option.seconds
            do {
                prefs = try await preferencesService.updatePreferences(
                    accessToken: token,
                    preferences: prefs
                )
                cachedAuthenticatedPreference = option
            } catch {
                syncBannerMessage = "Couldn’t save remembered timer."
            }
        } else {
            guestTimerStore.save(option)
        }
    }

    private func clearAuthenticatedRememberedTimer() async {
        guard let token = auth.accessToken else { return }
        do {
            var prefs = try await preferencesService.getPreferences(accessToken: token)
            prefs.rememberTimerOption = false
            prefs.rememberedTimerMode = nil
            prefs.rememberedTimerSeconds = nil
            _ = try await preferencesService.updatePreferences(
                accessToken: token,
                preferences: prefs
            )
            cachedAuthenticatedPreference = nil
        } catch {
            syncBannerMessage = "Couldn’t clear remembered timer."
        }
    }

    private func refreshRecoveryState() {
        guard let snapshot = try? activeSessionStore.load(), snapshot.isRecoverable else {
            recoverableSnapshot = nil
            showsRecoveryBanner = false
            return
        }
        recoverableSnapshot = snapshot
        showsRecoveryBanner = !showsActiveSession && !showsCaptureSource && !showsReviewSubmission
    }

    func refreshDraftState() {
        do {
            let expired = try draftStore.purgeExpired(
                retentionDays: DraftStore.defaultRetentionDays,
                now: dateProvider.now()
            )
            for draft in expired {
                try? imageStore.delete(fileName: draft.imageFileName)
            }
            recoverableDraft = try draftStore.mostRecentRecoverable()
            if let draft = recoverableDraft,
               let data = try? imageStore.readData(fileName: draft.imageFileName) {
                recoverableDraftThumbnail = UIImage(data: data)
            } else {
                recoverableDraftThumbnail = nil
            }
        } catch {
            recoverableDraft = nil
            recoverableDraftThumbnail = nil
        }
    }
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
