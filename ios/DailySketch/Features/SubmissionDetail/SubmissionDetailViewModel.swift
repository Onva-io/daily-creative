import Foundation
import Observation

@MainActor
@Observable
final class SubmissionDetailViewModel {
    enum State: Equatable {
        case loading
        case loaded(SubmissionModel)
        case failed(String)
    }

    private(set) var state: State = .loading

    private let submissionId: UUID
    private let submissionService: any SubmissionServing
    private let accessTokenProvider: () -> String?

    init(
        submissionId: UUID,
        submissionService: any SubmissionServing,
        accessTokenProvider: @escaping () -> String?
    ) {
        self.submissionId = submissionId
        self.submissionService = submissionService
        self.accessTokenProvider = accessTokenProvider
    }

    func load() async {
        state = .loading
        do {
            let submission = try await submissionService.getSubmission(
                accessToken: accessTokenProvider(),
                submissionId: submissionId
            )
            state = .loaded(submission)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    var timerLabel: String {
        guard case .loaded(let submission) = state else { return "" }
        if submission.timerMode == "no_timer" {
            return "No timer"
        }
        if let seconds = submission.timerSeconds {
            let minutes = seconds / 60
            return minutes == 1 ? "1 minute" : "\(minutes) minutes"
        }
        return "Timer"
    }

    var promptDateLabel: String {
        guard case .loaded(let submission) = state else { return "" }
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: submission.promptDate)
    }
}
