import Foundation
@preconcurrency import DailySketchAPI

struct StorySessionModel: Equatable, Sendable, Identifiable {
    let id: UUID
    let userId: UUID
    let promptId: UUID
    let timerMode: String
    let selectedTimerSeconds: Int?
    let status: String
    let startedAt: Date
    let pausedTotalSeconds: Int
    let timerCompletedAt: Date?
    let finishRequestedAt: Date?
    let completedAt: Date?
    let abandonedAt: Date?
}

enum StorySessionAPIError: LocalizedError, Equatable {
    case sessionNotFound
    case invalidTimerSelection
    case invalidSessionTransition
    case idempotencyKeyConflict
    case promptNotFound
    case sessionExpired
    case underlying(String)

    var errorDescription: String? {
        switch self {
        case .sessionNotFound:
            return "The requested story session could not be found."
        case .invalidTimerSelection:
            return "Timer mode and selected seconds are inconsistent."
        case .invalidSessionTransition:
            return "That lifecycle event is not valid for the current session state."
        case .idempotencyKeyConflict:
            return "This idempotency key was already used with a different request."
        case .promptNotFound:
            return "The requested prompt could not be found."
        case .sessionExpired:
            return AuthServiceError.sessionExpired.localizedDescription
        case .underlying(let message):
            return message
        }
    }
}

protocol StorySessionServing: Sendable {
    func createSession(
        accessToken: String,
        promptId: UUID,
        timerMode: String,
        selectedTimerSeconds: Int?,
        idempotencyKey: String?
    ) async throws -> StorySessionModel

    func recordEvent(
        accessToken: String,
        sessionId: UUID,
        eventType: String
    ) async throws -> StorySessionModel

    func abandonSession(
        accessToken: String,
        sessionId: UUID
    ) async throws -> StorySessionModel
}

struct StorySessionRepository: StorySessionServing {
    let baseURL: URL

    func createSession(
        accessToken: String,
        promptId: UUID,
        timerMode: String,
        selectedTimerSeconds: Int?,
        idempotencyKey: String? = nil
    ) async throws -> StorySessionModel {
        configureClient(accessToken: accessToken)
        guard let mode = TimerMode(rawValue: timerMode) else {
            throw StorySessionAPIError.invalidTimerSelection
        }
        do {
            let request = CreateStorySessionRequest(
                promptId: promptId,
                timerMode: mode,
                selectedTimerSeconds: selectedTimerSeconds
            )
            let session = try await StorySessionsAPI.createStorySession(
                createStorySessionRequest: request,
                idempotencyKey: idempotencyKey
            )
            return mapSession(session)
        } catch {
            throw mapAPIError(error)
        }
    }

    func recordEvent(
        accessToken: String,
        sessionId: UUID,
        eventType: String
    ) async throws -> StorySessionModel {
        configureClient(accessToken: accessToken)
        guard let type = StorySessionEventType(rawValue: eventType) else {
            throw StorySessionAPIError.invalidSessionTransition
        }
        do {
            let request = StorySessionEventRequest(
                eventType: type,
                clientOccurredAt: nil,
                metadata: nil
            )
            let session = try await StorySessionsAPI.postStorySessionEvent(
                sessionId: sessionId,
                storySessionEventRequest: request
            )
            return mapSession(session)
        } catch {
            throw mapAPIError(error)
        }
    }

    func abandonSession(
        accessToken: String,
        sessionId: UUID
    ) async throws -> StorySessionModel {
        configureClient(accessToken: accessToken)
        do {
            let session = try await StorySessionsAPI.abandonStorySession(sessionId: sessionId)
            return mapSession(session)
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

    private func mapSession(_ session: StorySession) -> StorySessionModel {
        StorySessionModel(
            id: session.id,
            userId: session.userId,
            promptId: session.promptId,
            timerMode: session.timerMode.rawValue,
            selectedTimerSeconds: session.selectedTimerSeconds,
            status: session.status.rawValue,
            startedAt: session.startedAt,
            pausedTotalSeconds: session.pausedTotalSeconds,
            timerCompletedAt: session.timerCompletedAt,
            finishRequestedAt: session.finishRequestedAt,
            completedAt: session.completedAt,
            abandonedAt: session.abandonedAt
        )
    }

    private func mapAPIError(_ error: Error) -> Error {
        if let errorResponse = error as? ErrorResponse {
            switch errorResponse {
            case .error(let code, let data, _, _):
                if code == 401 {
                    return StorySessionAPIError.sessionExpired
                }
                if let data,
                   let envelope = try? JSONDecoder().decode(StorySessionAPIErrorEnvelope.self, from: data) {
                    switch envelope.error.code {
                    case "session_not_found":
                        return StorySessionAPIError.sessionNotFound
                    case "invalid_timer_selection":
                        return StorySessionAPIError.invalidTimerSelection
                    case "invalid_session_transition":
                        return StorySessionAPIError.invalidSessionTransition
                    case "idempotency_key_conflict":
                        return StorySessionAPIError.idempotencyKeyConflict
                    case "prompt_not_found":
                        return StorySessionAPIError.promptNotFound
                    default:
                        return StorySessionAPIError.underlying(envelope.error.message)
                    }
                }
            }
        }
        return StorySessionAPIError.underlying(error.localizedDescription)
    }
}

private struct StorySessionAPIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}
