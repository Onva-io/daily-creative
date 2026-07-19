import Foundation
@preconcurrency import DailySketchAPI

struct ReflectionModel: Equatable, Sendable, Identifiable {
    let id: UUID
    let submissionId: UUID
    let userId: UUID
    let username: String
    let displayName: String
    let avatarURL: URL?
    let body: String
    let createdAt: Date
    let isAuthor: Bool
}

struct LikeStateModel: Equatable, Sendable {
    let liked: Bool
    let likeCount: Int
}

struct ReflectionPage: Equatable, Sendable {
    let items: [ReflectionModel]
    let nextCursor: String?
}

enum SocialAPIError: LocalizedError, Equatable {
    case sessionExpired
    case submissionNotFound
    case reflectionNotFound
    case reflectionForbidden
    case profileIncomplete
    case validationError(String)
    case underlying(String)

    var errorDescription: String? {
        switch self {
        case .sessionExpired:
            return "Your session expired. Sign in again."
        case .submissionNotFound:
            return "The requested sketch could not be found."
        case .reflectionNotFound:
            return "The requested reflection could not be found."
        case .reflectionForbidden:
            return "You can only delete your own reflection."
        case .profileIncomplete:
            return "Complete your profile before posting a reflection."
        case .validationError(let message):
            return message
        case .underlying(let message):
            return message
        }
    }
}

protocol LikeServing: Sendable {
    func likeSubmission(accessToken: String, submissionId: UUID) async throws -> LikeStateModel
    func unlikeSubmission(accessToken: String, submissionId: UUID) async throws -> LikeStateModel
}

protocol ReflectionServing: Sendable {
    func listReflections(
        accessToken: String?,
        submissionId: UUID,
        cursor: String?,
        limit: Int
    ) async throws -> ReflectionPage

    func createReflection(
        accessToken: String,
        submissionId: UUID,
        body: String,
        idempotencyKey: String?
    ) async throws -> ReflectionModel

    func deleteReflection(accessToken: String, reflectionId: UUID) async throws
}

protocol SocialServing: LikeServing, ReflectionServing {}

struct SocialRepository: SocialServing {
    let baseURL: URL

    func likeSubmission(accessToken: String, submissionId: UUID) async throws -> LikeStateModel {
        configureClient(accessToken: accessToken)
        do {
            let state = try await SubmissionsAPI.likeSubmission(submissionId: submissionId)
            return LikeStateModel(liked: state.liked, likeCount: state.likeCount)
        } catch {
            throw mapSocialAPIError(error)
        }
    }

    func unlikeSubmission(accessToken: String, submissionId: UUID) async throws -> LikeStateModel {
        configureClient(accessToken: accessToken)
        do {
            let state = try await SubmissionsAPI.unlikeSubmission(submissionId: submissionId)
            return LikeStateModel(liked: state.liked, likeCount: state.likeCount)
        } catch {
            throw mapSocialAPIError(error)
        }
    }

    func listReflections(
        accessToken: String?,
        submissionId: UUID,
        cursor: String?,
        limit: Int
    ) async throws -> ReflectionPage {
        configureClient(accessToken: accessToken)
        do {
            let page = try await SubmissionsAPI.listReflections(
                submissionId: submissionId,
                cursor: cursor,
                limit: limit
            )
            return ReflectionPage(
                items: page.items.map(mapReflection),
                nextCursor: page.nextCursor
            )
        } catch {
            throw mapSocialAPIError(error)
        }
    }

    func createReflection(
        accessToken: String,
        submissionId: UUID,
        body: String,
        idempotencyKey: String?
    ) async throws -> ReflectionModel {
        configureClient(accessToken: accessToken)
        do {
            let request = CreateReflectionRequest(body: body)
            let reflection = try await SubmissionsAPI.createReflection(
                submissionId: submissionId,
                createReflectionRequest: request,
                idempotencyKey: idempotencyKey
            )
            return mapReflection(reflection)
        } catch {
            throw mapSocialAPIError(error)
        }
    }

    func deleteReflection(accessToken: String, reflectionId: UUID) async throws {
        configureClient(accessToken: accessToken)
        do {
            try await ReflectionsAPI.deleteReflection(reflectionId: reflectionId)
        } catch {
            throw mapSocialAPIError(error)
        }
    }

    private func configureClient(accessToken: String?) {
        var base = baseURL.absoluteString
        if base.hasSuffix("/") {
            base.removeLast()
        }
        DailySketchAPIAPI.basePath = base
        if let accessToken {
            DailySketchAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"
            DailySketchAPITokenBridge.setBearerToken(accessToken)
        } else {
            DailySketchAPIAPI.customHeaders.removeValue(forKey: "Authorization")
        }
    }

    private func mapReflection(_ reflection: Reflection) -> ReflectionModel {
        ReflectionModel(
            id: reflection.id,
            submissionId: reflection.submissionId,
            userId: reflection.user.id,
            username: reflection.user.username,
            displayName: reflection.user.displayName,
            avatarURL: reflection.user.avatarUrl.flatMap(URL.init(string:)),
            body: reflection.body,
            createdAt: reflection.createdAt,
            isAuthor: reflection.isAuthor
        )
    }
}

func mapSocialAPIError(_ error: Error) -> Error {
    if let errorResponse = error as? ErrorResponse {
        switch errorResponse {
        case .error(let code, let data, _, _):
            if code == 401 {
                return SocialAPIError.sessionExpired
            }
            if let data,
               let envelope = try? JSONDecoder().decode(SocialAPIErrorEnvelope.self, from: data) {
                switch envelope.error.code {
                case "submission_not_found":
                    return SocialAPIError.submissionNotFound
                case "reflection_not_found":
                    return SocialAPIError.reflectionNotFound
                case "reflection_forbidden":
                    return SocialAPIError.reflectionForbidden
                case "profile_incomplete":
                    return SocialAPIError.profileIncomplete
                case "validation_error":
                    return SocialAPIError.validationError(envelope.error.message)
                default:
                    return SocialAPIError.underlying(envelope.error.message)
                }
            }
            if code == 404 {
                return SocialAPIError.submissionNotFound
            }
        }
    }
    return SocialAPIError.underlying(error.localizedDescription)
}

private struct SocialAPIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}

final class RecordingSocialRepository: SocialServing, @unchecked Sendable {
    private(set) var likeCallCount = 0
    private(set) var unlikeCallCount = 0
    private(set) var listCallCount = 0
    private(set) var createCallCount = 0
    private(set) var deleteCallCount = 0
    private(set) var lastLikedSubmissionId: UUID?
    private(set) var lastCreatedBody: String?

    var likeError: Error?
    var unlikeError: Error?
    var listError: Error?
    var createError: Error?
    var deleteError: Error?

    var nextLikeState = LikeStateModel(liked: true, likeCount: 1)
    var nextUnlikeState = LikeStateModel(liked: false, likeCount: 0)
    var nextPage = ReflectionPage(items: [], nextCursor: nil)
    var nextReflection: ReflectionModel?

    func likeSubmission(accessToken: String, submissionId: UUID) async throws -> LikeStateModel {
        likeCallCount += 1
        lastLikedSubmissionId = submissionId
        if let likeError { throw likeError }
        return nextLikeState
    }

    func unlikeSubmission(accessToken: String, submissionId: UUID) async throws -> LikeStateModel {
        unlikeCallCount += 1
        lastLikedSubmissionId = submissionId
        if let unlikeError { throw unlikeError }
        return nextUnlikeState
    }

    func listReflections(
        accessToken: String?,
        submissionId: UUID,
        cursor: String?,
        limit: Int
    ) async throws -> ReflectionPage {
        listCallCount += 1
        if let listError { throw listError }
        return nextPage
    }

    func createReflection(
        accessToken: String,
        submissionId: UUID,
        body: String,
        idempotencyKey: String?
    ) async throws -> ReflectionModel {
        createCallCount += 1
        lastCreatedBody = body
        if let createError { throw createError }
        if let nextReflection { return nextReflection }
        return ReflectionModel(
            id: UUID(),
            submissionId: submissionId,
            userId: UUID(),
            username: "tester",
            displayName: "Tester",
            avatarURL: nil,
            body: body,
            createdAt: Date(),
            isAuthor: true
        )
    }

    func deleteReflection(accessToken: String, reflectionId: UUID) async throws {
        deleteCallCount += 1
        if let deleteError { throw deleteError }
    }
}
