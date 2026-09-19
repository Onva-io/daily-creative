import Foundation
import Observation

enum TimedSessionPhase: Equatable {
    case running
    case paused
    case timerCompleted
    /// The timer part is over; the type-specific next step (capture, write…)
    /// is available.
    case readyToContinue
    case abandoned
}

/// Drives the shared timer screen for any creative type.
///
/// Owns the countdown/elapsed clock, pause/resume, local recovery snapshots,
/// and the generic server events (`paused`, `resumed`, `timer_completed`,
/// `finished_early`). The creative type supplies the stage event to post when
/// the user moves on (`postTimerStageEvent`) and what happens next
/// (`onContinue`).
@MainActor
@Observable
final class TimedSessionViewModel {
    private(set) var phase: TimedSessionPhase
    private(set) var displayedCountdownSeconds: Int
    private(set) var displayedElapsedSeconds: Int
    private(set) var syncPending = false
    private(set) var syncErrorMessage: String?
    private(set) var showsCancelConfirmation = false

    let creativeType: String
    let labels: TimedSessionLabels
    let promptId: UUID
    let promptWords: [String]
    let promptAccessibilityLabel: String
    let promptDate: Date
    let timerOption: TimerPreferenceOption
    let localSessionId: UUID

    private(set) var serverSessionId: UUID?
    private var startedAt: Date
    private var pausedAt: Date?
    private var pausedTotalSeconds: Int
    private let isGuest: Bool
    private var tickTask: Task<Void, Never>?
    private var didEmitTimerCompleted = false

    private let postTimerStageEvent: String?
    private let accessTokenProvider: () async -> String?
    private let sessionService: any CreativeSessionServing
    private let activeSessionStore: any ActiveSessionStoring
    private let dateProvider: any DateProviding
    private let analytics: (any AnalyticsTracking)?
    private let onEnded: () -> Void
    private let onContinue: () -> Void

    var sessionStartedAt: Date { startedAt }

    init(
        creativeType: String,
        labels: TimedSessionLabels,
        prompt: DailyPromptModel,
        timerOption: TimerPreferenceOption,
        localSessionId: UUID = UUID(),
        serverSessionId: UUID? = nil,
        startedAt: Date? = nil,
        pausedAt: Date? = nil,
        pausedTotalSeconds: Int = 0,
        lifecycle: ActiveSessionLifecycle = .active,
        syncPending: Bool = false,
        isGuest: Bool,
        postTimerStageEvent: String?,
        accessTokenProvider: @escaping () async -> String?,
        sessionService: any CreativeSessionServing,
        activeSessionStore: any ActiveSessionStoring,
        dateProvider: any DateProviding = SystemDateProvider(),
        analytics: (any AnalyticsTracking)? = nil,
        onEnded: @escaping () -> Void,
        onContinue: @escaping () -> Void = {}
    ) {
        self.creativeType = creativeType
        self.labels = labels
        self.promptId = prompt.id
        self.promptWords = prompt.words
        self.promptAccessibilityLabel = prompt.accessibilityLabel
        self.promptDate = prompt.promptDate
        self.timerOption = timerOption
        self.localSessionId = localSessionId
        self.serverSessionId = serverSessionId
        let now = dateProvider.now()
        self.startedAt = startedAt ?? now
        self.pausedAt = pausedAt
        self.pausedTotalSeconds = pausedTotalSeconds
        self.isGuest = isGuest
        self.syncPending = syncPending
        self.postTimerStageEvent = postTimerStageEvent
        self.accessTokenProvider = accessTokenProvider
        self.sessionService = sessionService
        self.activeSessionStore = activeSessionStore
        self.dateProvider = dateProvider
        self.analytics = analytics
        self.onEnded = onEnded
        self.onContinue = onContinue

        switch lifecycle {
        case .active:
            self.phase = .running
        case .paused:
            self.phase = .paused
        case .timerCompleted:
            self.phase = .timerCompleted
            self.didEmitTimerCompleted = true
        case .readyToContinue:
            self.phase = .readyToContinue
        case .abandoned:
            self.phase = .abandoned
        }

        self.displayedCountdownSeconds = timerOption.seconds ?? 0
        self.displayedElapsedSeconds = 0
        refreshDisplayedTime()
    }

    var isCountdown: Bool {
        timerOption != .noTimer
    }

    var canPause: Bool {
        phase == .running && isCountdown
    }

    var canResume: Bool {
        phase == .paused
    }

    var formattedCountdown: String {
        Self.formatClock(displayedCountdownSeconds)
    }

    var formattedElapsed: String {
        Self.formatClock(displayedElapsedSeconds)
    }

    func startTicking() {
        refreshDisplayedTime()
        persistSnapshot()
        tickTask?.cancel()
        tickTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 250_000_000)
                guard let self else { return }
                self.refreshDisplayedTime()
            }
        }
    }

    func stopTicking() {
        tickTask?.cancel()
        tickTask = nil
    }

    func pause() {
        guard canPause else { return }
        phase = .paused
        pausedAt = dateProvider.now()
        refreshDisplayedTime()
        persistSnapshot()
        analytics?.track(.sessionPaused)
        Task { await postEvent(CreativeSessionClientEvent.paused) }
    }

    func resume() {
        guard canResume, let pausedAt else { return }
        let delta = max(0, Int(dateProvider.now().timeIntervalSince(pausedAt)))
        pausedTotalSeconds += delta
        self.pausedAt = nil
        phase = .running
        refreshDisplayedTime()
        persistSnapshot()
        analytics?.track(.sessionResumed)
        Task { await postEvent(CreativeSessionClientEvent.resumed) }
    }

    func finish() {
        guard phase == .running || phase == .paused || phase == .timerCompleted else { return }
        if phase == .paused, let pausedAt {
            let delta = max(0, Int(dateProvider.now().timeIntervalSince(pausedAt)))
            pausedTotalSeconds += delta
            self.pausedAt = nil
        }
        enterReadyToContinue(emitFinishedEarly: phase != .timerCompleted)
    }

    func requestCancel() {
        showsCancelConfirmation = true
    }

    func dismissCancelConfirmation() {
        showsCancelConfirmation = false
    }

    func confirmCancel() {
        showsCancelConfirmation = false
        phase = .abandoned
        stopTicking()
        analytics?.track(.sessionAbandoned)
        Task {
            await abandonRemote()
            try? activeSessionStore.clear()
            onEnded()
        }
    }

    /// After the countdown ends, stay on this screen without a clock and move
    /// on when ready.
    func keepGoingAfterTimer() {
        guard phase == .timerCompleted else { return }
        phase = .readyToContinue
        persistSnapshot()
    }

    /// Move to the creative type's next step (capture, write…).
    func continueToNextStep() {
        if phase == .readyToContinue {
            onContinue()
            return
        }
        enterReadyToContinue(emitFinishedEarly: phase != .timerCompleted)
    }

    private func enterReadyToContinue(emitFinishedEarly: Bool) {
        phase = .readyToContinue
        persistSnapshot()
        Task {
            if emitFinishedEarly {
                analytics?.track(.sessionFinishedEarly)
                await postEvent(CreativeSessionClientEvent.finishedEarly)
            }
            if let postTimerStageEvent {
                await postEvent(postTimerStageEvent)
            }
            onContinue()
        }
    }

    func attachServerSessionId(_ id: UUID) {
        serverSessionId = id
        syncPending = false
        syncErrorMessage = nil
        persistSnapshot()
    }

    func markSyncPending(_ message: String?) {
        syncPending = true
        syncErrorMessage = message
        persistSnapshot()
    }

    private func refreshDisplayedTime() {
        let now = dateProvider.now()
        let pausedExtra: TimeInterval
        if phase == .paused, let pausedAt {
            pausedExtra = now.timeIntervalSince(pausedAt)
        } else {
            pausedExtra = 0
        }
        let elapsed = max(
            0,
            Int(now.timeIntervalSince(startedAt) - TimeInterval(pausedTotalSeconds) - pausedExtra)
        )
        displayedElapsedSeconds = elapsed

        guard isCountdown, let total = timerOption.seconds else { return }
        let remaining = max(0, total - elapsed)
        displayedCountdownSeconds = remaining

        if phase == .running, remaining == 0, !didEmitTimerCompleted {
            didEmitTimerCompleted = true
            phase = .timerCompleted
            persistSnapshot()
            analytics?.track(.timerCompleted)
            Task { await postEvent(CreativeSessionClientEvent.timerCompleted) }
        }
    }

    private func persistSnapshot() {
        let lifecycle: ActiveSessionLifecycle
        switch phase {
        case .running:
            lifecycle = .active
        case .paused:
            lifecycle = .paused
        case .timerCompleted:
            lifecycle = .timerCompleted
        case .readyToContinue:
            lifecycle = .readyToContinue
        case .abandoned:
            lifecycle = .abandoned
        }

        let snapshot = ActiveSessionSnapshot(
            id: localSessionId,
            serverSessionId: serverSessionId,
            creativeType: creativeType,
            promptId: promptId,
            promptWords: promptWords,
            promptAccessibilityLabel: promptAccessibilityLabel,
            timerMode: timerOption.mode,
            selectedTimerSeconds: timerOption.seconds,
            startedAt: startedAt,
            pausedAt: pausedAt,
            pausedTotalSeconds: pausedTotalSeconds,
            lifecycle: lifecycle,
            syncPending: syncPending,
            isGuest: isGuest
        )
        try? activeSessionStore.save(snapshot)
    }

    private func postEvent(_ eventType: String) async {
        guard let serverSessionId, let token = await accessTokenProvider() else { return }
        do {
            _ = try await sessionService.postEvent(
                accessToken: token,
                sessionId: serverSessionId,
                eventType: eventType,
                clientOccurredAt: dateProvider.now()
            )
        } catch {
            markSyncPending(error.localizedDescription)
        }
    }

    private func abandonRemote() async {
        guard let serverSessionId, let token = await accessTokenProvider() else { return }
        do {
            _ = try await sessionService.abandonSession(
                accessToken: token,
                sessionId: serverSessionId
            )
        } catch {
            markSyncPending(error.localizedDescription)
        }
    }

    static func formatClock(_ totalSeconds: Int) -> String {
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}
