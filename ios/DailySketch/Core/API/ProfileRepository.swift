import Foundation
@preconcurrency import DailySketchAPI

struct PublicProfileModel: Equatable, Sendable, Identifiable {
    let id: UUID
    let username: String
    let displayName: String
    let bio: String?
    let avatarURL: URL?
    let submissionCount: Int
    let currentStreak: Int
    let isSelf: Bool

    var streakLabel: String {
        if currentStreak == 1 {
            return "1-day streak"
        }
        return "\(currentStreak)-day streak"
    }

    var submissionCountLabel: String {
        let noun = ProductConfig.current.creativeTypeID == "story" ? "story" : "sketch"
        let plural = ProductConfig.current.creativeTypeID == "story" ? "stories" : "sketches"
        if submissionCount == 1 {
            return "1 \(noun)"
        }
        return "\(submissionCount) \(plural)"
    }
}

protocol ProfileFetching: Sendable {
    func fetchPublicProfile(
        username: String,
        accessToken: String?,
        creativeType: String?
    ) async throws -> PublicProfileModel

    func fetchUserSubmissions(
        username: String,
        accessToken: String?,
        cursor: String?,
        limit: Int,
        creativeType: String?
    ) async throws -> RecentFeedPage
}

struct ProfileRepository: ProfileFetching {
    let baseURL: URL

    func fetchPublicProfile(
        username: String,
        accessToken: String?,
        creativeType: String? = ProductConfig.current.creativeTypeID
    ) async throws -> PublicProfileModel {
        configureClient(accessToken: accessToken)
        do {
            let user = try await UsersAPI.getPublicUser(
                username: username,
                creativeType: FeedMapping.apiCreativeType(from: creativeType ?? ProductConfig.current.creativeTypeID)
            )
            return mapProfile(user)
        } catch {
            throw mapAPIError(error)
        }
    }

    func fetchUserSubmissions(
        username: String,
        accessToken: String?,
        cursor: String?,
        limit: Int,
        creativeType: String? = ProductConfig.current.creativeTypeID
    ) async throws -> RecentFeedPage {
        configureClient(accessToken: accessToken)
        do {
            let feed = try await UsersAPI.getUserSubmissions(
                username: username,
                cursor: cursor,
                limit: limit,
                creativeType: FeedMapping.apiCreativeType(from: creativeType ?? ProductConfig.current.creativeTypeID)
            )
            return RecentFeedPage(
                items: feed.items.compactMap(FeedMapping.mapItem),
                nextCursor: feed.nextCursor
            )
        } catch {
            throw mapAPIError(error)
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

    private func mapProfile(_ user: PublicUser) -> PublicProfileModel {
        PublicProfileModel(
            id: user.id,
            username: user.username,
            displayName: user.displayName,
            bio: user.bio,
            avatarURL: user.avatarUrl.flatMap(URL.init(string:)),
            submissionCount: user.submissionCount,
            currentStreak: user.currentStreak,
            isSelf: user.isSelf
        )
    }

    private func mapAPIError(_ error: Error) -> Error {
        if let errorResponse = error as? ErrorResponse {
            switch errorResponse {
            case .error(let code, let data, _, _):
                if code == 404 {
                    return ProfileAPIError.underlying("The requested profile could not be found.")
                }
                if let data,
                   let envelope = try? JSONDecoder().decode(ProfileAPIErrorEnvelope.self, from: data) {
                    return ProfileAPIError.underlying(envelope.error.message)
                }
            }
        }
        return ProfileAPIError.underlying(error.localizedDescription)
    }
}

private struct ProfileAPIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}

final class RecordingProfileFetcher: ProfileFetching, @unchecked Sendable {
    var profile: PublicProfileModel?
    var pages: [RecentFeedPage] = []
    var error: Error?
    private(set) var fetchProfileCallCount = 0
    private(set) var fetchSubmissionsCallCount = 0
    private(set) var lastCursor: String?

    func fetchPublicProfile(
        username: String,
        accessToken: String?,
        creativeType: String?
    ) async throws -> PublicProfileModel {
        fetchProfileCallCount += 1
        _ = creativeType
        if let error { throw error }
        if let profile { return profile }
        return PublicProfileModel(
            id: UUID(),
            username: username,
            displayName: username,
            bio: nil,
            avatarURL: nil,
            submissionCount: 0,
            currentStreak: 0,
            isSelf: false
        )
    }

    func fetchUserSubmissions(
        username: String,
        accessToken: String?,
        cursor: String?,
        limit: Int,
        creativeType: String?
    ) async throws -> RecentFeedPage {
        fetchSubmissionsCallCount += 1
        lastCursor = cursor
        _ = creativeType
        if let error { throw error }
        if pages.isEmpty {
            return RecentFeedPage(items: [], nextCursor: nil)
        }
        let index = cursor == nil ? 0 : min(1, pages.count - 1)
        return pages[index]
    }
}
