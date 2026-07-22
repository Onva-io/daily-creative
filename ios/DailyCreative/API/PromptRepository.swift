import Foundation
@preconcurrency import DailyCreativeAPI

protocol PromptFetching: Sendable {
    func fetchTodaysPrompt() async throws -> DailyPromptModel
}

protocol FeedFetching: Sendable {
    func fetchRecentFeed(
        accessToken: String?,
        cursor: String?,
        limit: Int,
        creativeType: String?
    ) async throws -> RecentFeedPage
}

struct PromptRepository: PromptFetching, FeedFetching {
    let baseURL: URL

    func fetchTodaysPrompt() async throws -> DailyPromptModel {
        configureClient(accessToken: nil)
        do {
            let prompt = try await PromptsAPI.getTodaysPrompt()
            return mapPrompt(prompt)
        } catch {
            throw mapAPIError(error)
        }
    }

    func fetchRecentFeed(
        accessToken: String?,
        cursor: String?,
        limit: Int,
        creativeType: String? = ProductConfig.current.creativeTypeID
    ) async throws -> RecentFeedPage {
        configureClient(accessToken: accessToken)
        do {
            let feed = try await FeedAPI.getRecentFeed(
                creativeType: FeedMapping.apiCreativeType(from: creativeType ?? ProductConfig.current.creativeTypeID),
                cursor: cursor,
                limit: limit
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
        DailyCreativeAPIAPI.basePath = base
        if let accessToken {
            DailyCreativeAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"
            DailyCreativeAPITokenBridge.setBearerToken(accessToken)
        } else {
            DailyCreativeAPIAPI.customHeaders.removeValue(forKey: "Authorization")
        }
    }

    private func mapPrompt(_ prompt: DailyPrompt) -> DailyPromptModel {
        DailyPromptModel(
            id: prompt.id,
            promptDate: prompt.promptDate,
            word1: prompt.word1,
            word2: prompt.word2,
            word3: prompt.word3,
            status: prompt.status.rawValue,
            publishedAt: prompt.publishedAt
        )
    }

    private func mapAPIError(_ error: Error) -> Error {
        if let errorResponse = error as? ErrorResponse {
            switch errorResponse {
            case .error(let code, let data, _, _):
                if let data,
                   let envelope = try? JSONDecoder().decode(PromptAPIErrorEnvelope.self, from: data) {
                    if envelope.error.code == "prompt_not_found" || code == 404 {
                        return PromptAPIError.promptNotFound
                    }
                    return PromptAPIError.underlying(envelope.error.message)
                }
                if code == 404 {
                    return PromptAPIError.promptNotFound
                }
            }
        }
        return PromptAPIError.underlying(error.localizedDescription)
    }
}

private struct PromptAPIErrorEnvelope: Decodable {
    struct Body: Decodable {
        let code: String
        let message: String
    }

    let error: Body
}

final class RecordingPromptFetcher: PromptFetching, FeedFetching, @unchecked Sendable {
    var prompt: DailyPromptModel?
    var promptError: Error?
    var feed: RecentFeedPage = RecentFeedPage(items: [], nextCursor: nil)
    var feedPages: [String?: RecentFeedPage] = [:]
    var feedError: Error?
    private(set) var todaysPromptCallCount = 0
    private(set) var recentFeedCallCount = 0
    private(set) var lastFeedCursor: String?
    private(set) var lastFeedLimit: Int?

    func fetchTodaysPrompt() async throws -> DailyPromptModel {
        todaysPromptCallCount += 1
        if let promptError {
            throw promptError
        }
        guard let prompt else {
            throw PromptAPIError.promptNotFound
        }
        return prompt
    }

    func fetchRecentFeed(cursor: String?, limit: Int) async throws -> RecentFeedPage {
        try await fetchRecentFeed(accessToken: nil, cursor: cursor, limit: limit, creativeType: nil)
    }

    func fetchRecentFeed(
        accessToken: String?,
        cursor: String?,
        limit: Int,
        creativeType: String?
    ) async throws -> RecentFeedPage {
        lastFeedCursor = cursor
        lastFeedLimit = limit
        recentFeedCallCount += 1
        _ = creativeType
        if let feedError {
            throw feedError
        }
        if let page = feedPages[cursor] {
            return page
        }
        return feed
    }
}
