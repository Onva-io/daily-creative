import Foundation
import Observation

enum HomePromptState: Equatable {
    case loading
    case loaded(DailyPromptModel)
    case missing
    case failed(String)
}

enum HomeFeedState: Equatable {
    case loading
    case empty
    case loaded([FeedItemModel])
    case failed(String)
}

@MainActor
@Observable
final class HomeViewModel {
    private(set) var promptState: HomePromptState = .loading
    private(set) var feedState: HomeFeedState = .loading
    private(set) var cachedPrompt: DailyPromptModel?
    private(set) var feedItems: [FeedItemModel] = []
    private(set) var nextFeedCursor: String?
    private(set) var isLoadingMoreFeed = false
    private(set) var todaysPublished: [PublishedLocalSubmission] = []
    private(set) var likeErrorMessage: String?
    private(set) var pendingLikeSubmissionId: UUID?
    var showsAuthSheet = false
    var authSheetMode: AuthenticationView.Mode = .signUp

    private let promptFetcher: any PromptFetching
    private let feedFetcher: any FeedFetching
    private let socialService: any SocialServing
    private let publishedStore: any PublishedSubmissionStoring
    private let isAuthenticated: () -> Bool
    private let accessTokenProvider: () -> String?
    let sketchFlow: SketchFlowViewModel
    private let feedPageSize = 20
    private var likeInFlightIDs: Set<UUID> = []

    init(
        promptFetcher: any PromptFetching,
        feedFetcher: any FeedFetching,
        socialService: any SocialServing,
        publishedStore: any PublishedSubmissionStoring,
        sketchFlow: SketchFlowViewModel,
        isAuthenticated: @escaping () -> Bool = { false },
        accessTokenProvider: @escaping () -> String? = { nil }
    ) {
        self.promptFetcher = promptFetcher
        self.feedFetcher = feedFetcher
        self.socialService = socialService
        self.publishedStore = publishedStore
        self.sketchFlow = sketchFlow
        self.isAuthenticated = isAuthenticated
        self.accessTokenProvider = accessTokenProvider
    }

    var canStartSketch: Bool {
        if case .loaded = promptState {
            return true
        }
        return false
    }

    var hasSketchedToday: Bool {
        !todaysPublished.isEmpty
    }

    var loadedPrompt: DailyPromptModel? {
        if case .loaded(let prompt) = promptState {
            return prompt
        }
        return cachedPrompt
    }

    var promptWords: [String]? {
        loadedPrompt?.words
    }

    var promptAccessibilityLabel: String {
        loadedPrompt?.accessibilityLabel ?? "Today’s prompt is loading."
    }

    var primarySketchButtonTitle: String {
        hasSketchedToday ? "Create Another Sketch" : "Start Sketch"
    }

    var viewMySketchTitle: String {
        todaysPublished.count > 1 ? "View My Sketches" : "View My Sketch"
    }

    var canLoadMoreFeed: Bool {
        nextFeedCursor != nil && !isLoadingMoreFeed
    }

    func load() async {
        sketchFlow.prepareOnAppear()
        refreshPublishedToday()
        async let promptLoad: Void = loadPrompt()
        async let feedLoad: Void = loadFeed(reset: true)
        _ = await (promptLoad, feedLoad)
    }

    func refresh() async {
        refreshPublishedToday()
        async let promptLoad: Void = loadPrompt()
        async let feedLoad: Void = loadFeed(reset: true)
        _ = await (promptLoad, feedLoad)
    }

    func refreshPublishedToday() {
        guard let prompt = loadedPrompt ?? cachedPrompt else {
            todaysPublished = []
            return
        }
        todaysPublished = (try? publishedStore.forPromptDate(prompt.promptDate)) ?? []
    }

    func retryPrompt() async {
        await loadPrompt()
    }

    func retryFeed() async {
        await loadFeed(reset: true)
    }

    func loadMoreFeedIfNeeded(currentItem item: FeedItemModel) async {
        guard canLoadMoreFeed else { return }
        guard let index = feedItems.firstIndex(where: { $0.id == item.id }) else { return }
        let thresholdIndex = max(feedItems.count - 4, 0)
        guard index >= thresholdIndex else { return }
        await loadFeed(reset: false)
    }

    func removeFeedItem(id: UUID) {
        feedItems.removeAll { $0.id == id }
        if feedItems.isEmpty {
            feedState = .empty
            nextFeedCursor = nil
        } else {
            feedState = .loaded(feedItems)
        }
    }

    func applyLikeState(submissionId: UUID, liked: Bool, likeCount: Int) {
        guard let index = feedItems.firstIndex(where: { $0.id == submissionId }) else { return }
        feedItems[index] = feedItems[index].withLikeState(liked: liked, likeCount: likeCount)
        feedState = .loaded(feedItems)
    }

    func toggleLike(itemId: UUID) async {
        guard let index = feedItems.firstIndex(where: { $0.id == itemId }) else { return }
        guard isAuthenticated(), let token = accessTokenProvider() else {
            pendingLikeSubmissionId = itemId
            authSheetMode = .signUp
            showsAuthSheet = true
            return
        }
        guard !likeInFlightIDs.contains(itemId) else { return }

        let previous = feedItems[index]
        let nextLiked = !previous.viewerHasLiked
        let nextCount = max(0, previous.likeCount + (nextLiked ? 1 : -1))
        feedItems[index] = previous.withLikeState(liked: nextLiked, likeCount: nextCount)
        feedState = .loaded(feedItems)
        likeErrorMessage = nil
        likeInFlightIDs.insert(itemId)
        defer { likeInFlightIDs.remove(itemId) }

        do {
            let result: LikeStateModel
            if nextLiked {
                result = try await socialService.likeSubmission(
                    accessToken: token,
                    submissionId: itemId
                )
            } else {
                result = try await socialService.unlikeSubmission(
                    accessToken: token,
                    submissionId: itemId
                )
            }
            if let refreshedIndex = feedItems.firstIndex(where: { $0.id == itemId }) {
                feedItems[refreshedIndex] = feedItems[refreshedIndex].withLikeState(
                    liked: result.liked,
                    likeCount: result.likeCount
                )
                feedState = .loaded(feedItems)
            }
        } catch {
            if let rollbackIndex = feedItems.firstIndex(where: { $0.id == itemId }) {
                feedItems[rollbackIndex] = previous
                feedState = .loaded(feedItems)
            }
            likeErrorMessage = error.localizedDescription
        }
    }

    func handleAuthenticationCompleted() async {
        showsAuthSheet = false
        guard let pendingId = pendingLikeSubmissionId else { return }
        pendingLikeSubmissionId = nil
        await toggleLike(itemId: pendingId)
    }

    func clearLikeError() {
        likeErrorMessage = nil
    }

    func startSketch() {
        guard let prompt = loadedPrompt else { return }
        sketchFlow.startSketch(prompt: prompt)
    }

    private func loadPrompt() async {
        if let cachedPrompt {
            promptState = .loaded(cachedPrompt)
        } else {
            promptState = .loading
        }

        do {
            let prompt = try await promptFetcher.fetchTodaysPrompt()
            cachedPrompt = prompt
            promptState = .loaded(prompt)
            refreshPublishedToday()
        } catch let error as PromptAPIError where error == .promptNotFound {
            cachedPrompt = nil
            promptState = .missing
            todaysPublished = []
        } catch {
            if cachedPrompt == nil {
                promptState = .failed(error.localizedDescription)
            }
        }
    }

    private func loadFeed(reset: Bool) async {
        if reset {
            feedState = feedItems.isEmpty ? .loading : feedState
            isLoadingMoreFeed = false
        } else {
            guard let nextFeedCursor, !isLoadingMoreFeed else { return }
            isLoadingMoreFeed = true
            _ = nextFeedCursor
        }

        let cursor = reset ? nil : nextFeedCursor
        do {
            let page = try await feedFetcher.fetchRecentFeed(
                accessToken: accessTokenProvider(),
                cursor: cursor,
                limit: feedPageSize
            )
            if reset {
                feedItems = page.items
            } else {
                let existingIDs = Set(feedItems.map(\.id))
                let appended = page.items.filter { !existingIDs.contains($0.id) }
                feedItems.append(contentsOf: appended)
            }
            nextFeedCursor = page.nextCursor
            feedState = feedItems.isEmpty ? .empty : .loaded(feedItems)
        } catch {
            if reset && feedItems.isEmpty {
                feedState = .failed(
                    "Couldn’t load community sketches. Check your connection and try again."
                )
            }
            // Keep previously loaded feed visible on pagination failure.
        }
        isLoadingMoreFeed = false
    }
}
