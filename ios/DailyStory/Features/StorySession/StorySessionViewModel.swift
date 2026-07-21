import Foundation
import Observation

@MainActor
@Observable
final class StorySessionViewModel {
    let promptWords: [String]?
    let showsTimer: Bool
    var timerDisplay: String = "5:00"
    var isPaused: Bool = false
    var isCompleted: Bool = false

    private let sessionId: UUID
    private let totalSeconds: Int?
    private var remainingSeconds: Int
    private var timerTask: Task<Void, Never>?
    private let sessionService: any StorySessionServing
    private let accessToken: String
    var onTimerCompleted: (() -> Void)?
    var onFinishedEarly: (() -> Void)?

    init(
        sessionId: UUID,
        promptWords: [String]?,
        timerMode: String,
        timerSeconds: Int?,
        sessionService: any StorySessionServing,
        accessToken: String,
        onTimerCompleted: (() -> Void)? = nil,
        onFinishedEarly: (() -> Void)? = nil
    ) {
        self.sessionId = sessionId
        self.promptWords = promptWords
        self.showsTimer = timerMode == "countdown"
        self.totalSeconds = timerSeconds
        self.remainingSeconds = timerSeconds ?? 0
        self.sessionService = sessionService
        self.accessToken = accessToken
        self.onTimerCompleted = onTimerCompleted
        self.onFinishedEarly = onFinishedEarly
        updateTimerDisplay()
        if showsTimer {
            startTimer()
        }
    }

    func pause() {
        isPaused = true
        timerTask?.cancel()
        Task {
            try? await sessionService.recordEvent(
                accessToken: accessToken,
                sessionId: sessionId,
                eventType: "paused"
            )
        }
    }

    func resume() {
        isPaused = false
        Task {
            try? await sessionService.recordEvent(
                accessToken: accessToken,
                sessionId: sessionId,
                eventType: "resumed"
            )
        }
        startTimer()
    }

    func finishEarly() {
        timerTask?.cancel()
        isCompleted = true
        Task {
            try? await sessionService.recordEvent(
                accessToken: accessToken,
                sessionId: sessionId,
                eventType: "finished_early"
            )
            await MainActor.run { onFinishedEarly?() }
        }
    }

    func abandon() {
        timerTask?.cancel()
        Task {
            try? await sessionService.abandonSession(
                accessToken: accessToken,
                sessionId: sessionId
            )
        }
    }

    private func startTimer() {
        timerTask = Task {
            while !Task.isCancelled && remainingSeconds > 0 {
                try? await Task.sleep(for: .seconds(1))
                guard !Task.isCancelled else { break }
                remainingSeconds -= 1
                updateTimerDisplay()
            }
            if remainingSeconds <= 0 && !Task.isCancelled {
                isCompleted = true
                try? await sessionService.recordEvent(
                    accessToken: accessToken,
                    sessionId: sessionId,
                    eventType: "timer_completed"
                )
                await MainActor.run { onTimerCompleted?() }
            }
        }
    }

    private func updateTimerDisplay() {
        let minutes = remainingSeconds / 60
        let seconds = remainingSeconds % 60
        timerDisplay = String(format: "%d:%02d", minutes, seconds)
    }
}
