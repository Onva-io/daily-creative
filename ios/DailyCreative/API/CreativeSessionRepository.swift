import Foundation
@preconcurrency import DailyCreativeAPI

/// Client mirror of the API's unified `CreativeSession`.
///
/// Generic lifecycle fields are flat. `stage` carries the type-owned sub-state
/// (e.g. `ready_for_photo`, `uploading`, `writing`) and is opaque to shared code.
struct CreativeSessionModel: Equatable, Sendable, Identifiable {
    let id: UUID
    let userId: UUID
    let promptId: UUID
    let creativeType: String
    let timerMode: String
    let selectedTimerSeconds: Int?
    let status: String
    let stage: String?
    let startedAt: Date
    let pausedTotalSeconds: Int
    let timerCompletedAt: Date?
    let finishRequestedAt: Date?
    let abandonedAt: Date?
}

enum CreativeSessionAPIError: LocalizedError, Equatable {
    case sessionNotFound
    case invalidTimerSelection
    case invalidSessionTransition
    case idempotencyKeyConflict
    case promptNotFound
    case promptDateOutOfWindow
    case sessionExpired
    case underlying(String)

    var errorDescription: String? {
        switch self {
        case .sessionNotFound:
            return "The requested session could not be found."
        case .invalidTimerSelection:
            return "Timer mode and selected seconds are inconsistent."
        case .invalidSessionTransition:
            return "That lifecycle event is not valid for the current session state."
        case .idempotencyKeyConflict:
            return "This idempotency key was already used with a different request."
        case .promptNotFound:
            return "The requested prompt could not be found."
        case .promptDateOutOfWindow:
            return "This session is too old to publish. Start again with today's inspiration."
        case .sessionExpired:
            return AuthServiceError.sessionExpired.localizedDescription
        case .underlying(let message):
            return message
        }
    }
}

/// Generic client events every creative type accepts.
enum CreativeSessionClientEvent {
    static let paused = "paused"
    static let resumed = "resumed"
    static let timerCompleted = "timer_completed"
    static let finishedEarly = "finished_early"
}

protocol CreativeSessionServing: Sendable {
    func createSession(
        accessToken: String,
        creativeType: String,
        promptId: UUID,
        timerMode: String,
        selectedTimerSeconds: Int?,
        clientTimezone: String?,
        clientSessionId: String?,
        clientStartedAt: Date?,
        idempotencyKey: String
    ) async throws -> CreativeSessionModel

    func postEvent(
        accessToken: String,
        sessionId: UUID,
        eventType: String,
        clientOccurredAt: Date?
    ) async throws -> CreativeSessionModel

    func abandonSession(
        accessToken: String,
        sessionId: UUID
    ) async throws -> CreativeSessionModel
}

struct CreativeSessionRepository: CreativeSessionServing {
    let baseURL: URL

    func createSession(
        accessToken: String,
        creativeType: String,
        promptId: UUID,
        timerMode: String,
        selectedTimerSeconds: Int?,
        clientTimezone: String?,
        clientSessionId: String?,
        clientStartedAt: Date?,
        idempotencyKey: String
    ) async throws -> CreativeSessionModel {
        configureClient(accessToken: accessToken)
        guard let mode = TimerMode(rawValue: timerMode) else {
            throw CreativeSessionAPIError.invalidTimerSelection
        }
        guard let apiCreativeType = CreativeType(rawValue: creativeType) else {
            throw CreativeSessionAPIError.underlying("Unsupported creative type.")
        }
        do {
            let request = CreateSessionRequest(
                creativeType: apiCreativeType,
                promptId: promptId,
                timerMode: mode,
                selectedTimerSeconds: selectedTimerSeconds,
                clientTimezone: clientTimezone,
                clientSessionId: clientSessionId,
                clientStartedAt: clientStartedAt
            )
            let session = try await SessionsAPI.createSession(
                createSessionRequest: request,
                idempotencyKey: idempotencyKey
            )
            return mapSession(session)
        } catch {
            throw mapAPIError(error)
        }
    }

    func postEvent(
        accessToken: String,
        sessionId: UUID,
        eventType: String,
        clientOccurredAt: Date?
    ) async throws -> CreativeSessionModel {
        configureClient(accessToken: accessToken)
        do {
            let request = SessionEventRequest(
                eventType: eventType,
                clientOccurredAt: clientOccurredAt,
                metadata: nil
            )
            let session = try await SessionsAPI.postSessionEvent(
                sessionId: sessionId,
                sessionEventRequest: request
            )
            return mapSession(session)
        } catch {
            throw mapAPIError(error)
        }
    }

    func abandonSession(
        accessToken: String,
        sessionId: UUID
    ) async throws -> CreativeSessionModel {
        configureClient(accessToken: accessToken)
        do {
            let session = try await SessionsAPI.abandonSession(sessionId: sessionId)
            return mapSession(session)
        } catch {
            throw mapAPIError(error)
        }
    }

    private func configureClient(accessToken: String) {
        DailyCreativeAPIClientConfig.configure(baseURL: baseURL, accessToken: accessToken)
    }

    private func mapSession(_ session: CreativeSession) -> CreativeSessionModel {
        CreativeSessionModel(
            id: session.id,
            userId: session.userId,
            promptId: session.promptId,
            creativeType: session.creativeType.rawValue,
            timerMode: session.timerMode.rawValue,
            selectedTimerSeconds: session.selectedTimerSeconds,
            status: session.status.rawValue,
            stage: session.stage,
            startedAt: session.startedAt,
            pausedTotalSeconds: session.pausedTotalSeconds,
            timerCompletedAt: session.timerCompletedAt,
            finishRequestedAt: session.finishRequestedAt,
            abandonedAt: session.abandonedAt
        )
    }

    private func mapAPIError(_ error: Error) -> Error {
        if let errorResponse = error as? ErrorResponse {
            switch errorResponse {
            case .error(let code, let data, _, _):
                if code == 401 {
                    return CreativeSessionAPIError.sessionExpired
                }
                if let data,
                   let envelope = try? JSONDecoder().decode(CreativeSessionAPIErrorEnvelope.self, from: data) {
                    switch envelope.error.code {
                    case "session_not_found":
                        return CreativeSessionAPIError.sessionNotFound
                    case "invalid_timer_selection":
                        return CreativeSessionAPIError.invalidTimerSelection
                    case "invalid_session_transition":
                        return CreativeSessionAPIError.invalidSessionTransition
                    case "idempotency_key_conflict":
                        return CreativeSessionAPIError.idempotencyKeyConflict
                    case "prompt_not_found":
                        return CreativeSessionAPIError.promptNotFound
                    case "prompt_date_out_of_window":
                        return CreativeSessionAPIError.promptDateOutOfWindow
                    default:
                        return CreativeSessionAPIError.underlying(envelope.error.message)
                    }
                }
            }
        }
        return CreativeSessionAPIError.underlying(error.localizedDescription)
    }
}

private struct CreativeSessionAPIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}

final class RecordingCreativeSessionRepository: CreativeSessionServing, @unchecked Sendable {
    private(set) var createCallCount = 0
    private(set) var eventCallCount = 0
    private(set) var abandonCallCount = 0
    private(set) var lastAccessToken: String?
    private(set) var lastCreativeType: String?
    private(set) var lastEventType: String?
    private(set) var lastClientStartedAt: Date?
    var createError: Error?
    var eventError: Error?
    var abandonError: Error?
    var nextSession: CreativeSessionModel?

    func createSession(
        accessToken: String,
        creativeType: String,
        promptId: UUID,
        timerMode: String,
        selectedTimerSeconds: Int?,
        clientTimezone: String?,
        clientSessionId: String?,
        clientStartedAt: Date?,
        idempotencyKey: String
    ) async throws -> CreativeSessionModel {
        createCallCount += 1
        lastAccessToken = accessToken
        lastCreativeType = creativeType
        lastClientStartedAt = clientStartedAt
        if let createError {
            throw createError
        }
        if let nextSession {
            return nextSession
        }
        return CreativeSessionModel(
            id: UUID(),
            userId: UUID(),
            promptId: promptId,
            creativeType: creativeType,
            timerMode: timerMode,
            selectedTimerSeconds: selectedTimerSeconds,
            status: "active",
            stage: nil,
            startedAt: Date(),
            pausedTotalSeconds: 0,
            timerCompletedAt: nil,
            finishRequestedAt: nil,
            abandonedAt: nil
        )
    }

    func postEvent(
        accessToken: String,
        sessionId: UUID,
        eventType: String,
        clientOccurredAt: Date?
    ) async throws -> CreativeSessionModel {
        eventCallCount += 1
        lastAccessToken = accessToken
        lastEventType = eventType
        if let eventError {
            throw eventError
        }
        return CreativeSessionModel(
            id: sessionId,
            userId: UUID(),
            promptId: UUID(),
            creativeType: lastCreativeType ?? "sketch",
            timerMode: "countdown",
            selectedTimerSeconds: 300,
            status: eventType == "paused" ? "paused" : "active",
            stage: nil,
            startedAt: Date(),
            pausedTotalSeconds: 0,
            timerCompletedAt: nil,
            finishRequestedAt: nil,
            abandonedAt: nil
        )
    }

    func abandonSession(
        accessToken: String,
        sessionId: UUID
    ) async throws -> CreativeSessionModel {
        abandonCallCount += 1
        lastAccessToken = accessToken
        if let abandonError {
            throw abandonError
        }
        return CreativeSessionModel(
            id: sessionId,
            userId: UUID(),
            promptId: UUID(),
            creativeType: lastCreativeType ?? "sketch",
            timerMode: "countdown",
            selectedTimerSeconds: 300,
            status: "abandoned",
            stage: nil,
            startedAt: Date(),
            pausedTotalSeconds: 0,
            timerCompletedAt: nil,
            finishRequestedAt: nil,
            abandonedAt: Date()
        )
    }
}
