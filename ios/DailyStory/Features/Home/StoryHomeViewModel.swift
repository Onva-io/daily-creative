import Foundation
import Observation

@MainActor
@Observable
final class StoryHomeViewModel {
    private(set) var promptState: HomePromptState = .loading
    private(set) var feedState: HomeFeedState = .loading
    private(set) var cachedPrompt: DailyPromptModel?
    private(set) var feedItems: [FeedItemModel] = []
    private(set) var nextFeedCursor: String?
    private(set) var isLoadingMoreFeed = false
    private(set) var todaysPublished: [PublishedLocalSubmission] = []
    private(set) var likeErrorMessage: String?
    private(set) var isOffline = false

    private let promptFetcher: any PromptFetching
    private let feedFetcher: any FeedFetching
    private let socialService: any SocialServing
    private let publishedStore: any PublishedSubmissionStoring
    private let homeCacheStore: any HomeCacheStoring
    private let networkMonitor: any NetworkMonitoring
    private let analytics: any AnalyticsTracking
    private let dateProvider: any DateProviding
    private let isAuthenticated: () -> Bool
    private let accessTokenProvider: () -> String?
    private let feedPageSize = 20
    private var likeInFlightIDs: Set<UUID> = []
    private var lastPromptSyncedAt: Date?
    private var didCompleteInitialLoad = false

    init(
        promptFetcher: any PromptFetching,
        feedFetcher: any FeedFetching,
        socialService: any SocialServing,
        publishedStore: any PublishedSubmissionStoring,
        homeCacheStore: any HomeCacheStoring,
        networkMonitor: any NetworkMonitoring,
        analytics: any AnalyticsTracking,
        dateProvider: any DateProviding = SystemDateProvider(),
        isAuthenticated: @escaping () -> Bool = { false },
        accessTokenProvider: @escaping () -> String? = { nil }
    ) {
        self.promptFetcher = promptFetcher
        self.feedFetcher = feedFetcher
        self.socialService = socialService
        self.publishedStore = publishedStore
        self.homeCacheStore = homeCacheStore
        self.networkMonitor = networkMonitor
        self.analytics = analytics
        self.dateProvider = dateProvider
        self.isAuthenticated = isAuthenticated
        self.accessTokenProvider = accessTokenProvider
        restoreCachedHomeSnapshot()
    }

    var loadedPrompt: DailyPromptModel? {
        if case .loaded(let prompt) = promptState {
            return prompt
        }
        return cachedPrompt
    }

    var hasPublishedToday: Bool {
        !todaysPublished.isEmpty
    }

    var offlineIndicatorMessage: String? {
        guard isOffline else { return nil }
        if loadedPrompt != nil {
            return "You’re offline. Showing cached inspiration."
        }
        return "You’re offline. Some actions need a connection."
    }

    var canLoadMoreFeed: Bool {
        nextFeedCursor != nil && !isLoadingMoreFeed && networkMonitor.isOnline
    }

    func load() async {
        syncOfflineState()
        refreshPublishedToday()
        async let promptLoad: Void = loadPrompt()
        async let feedLoad: Void = loadFeed(reset: true)
        _ = await (promptLoad, feedLoad)
        didCompleteInitialLoad = true
    }

    func refresh() async {
        syncOfflineState()
        refreshPublishedToday()
        async let promptLoad: Void = loadPrompt()
        async let feedLoad: Void = loadFeed(reset: true)
        _ = await (promptLoad, feedLoad)
    }

    /// Called when the app returns to the foreground. Hides stale inspiration immediately
    /// (15+ minutes asleep or UTC Prompt Date boundary crossed), then refreshes.
    func handleSceneBecameActive() async {
        guard didCompleteInitialLoad else { return }
        guard shouldHideCachedPromptWhileRefreshing() else { return }
        if networkMonitor.isOnline {
            promptState = .loading
        }
        await refresh()
    }

    func retryPrompt() async {
        await loadPrompt()
    }

    func retryFeed() async {
        await loadFeed(reset: true)
    }

    func syncOfflineState() {
        isOffline = !networkMonitor.isOnline
    }

    func refreshPublishedToday() {
        guard let prompt = loadedPrompt ?? cachedPrompt else {
            todaysPublished = []
            return
        }
        todaysPublished = (try? publishedStore.forPromptDate(prompt.promptDate)) ?? []
    }

    func clearLikeError() {
        likeErrorMessage = nil
    }

    func toggleLike(itemId: UUID) async {
        guard isAuthenticated() else {
            likeErrorMessage = "Sign in to like stories."
            return
        }
        guard let token = accessTokenProvider() else { return }
        guard networkMonitor.isOnline else {
            likeErrorMessage = "Reconnect to update Likes."
            return
        }
        guard !likeInFlightIDs.contains(itemId),
              let index = feedItems.firstIndex(where: { $0.id == itemId })
        else {
            return
        }

        likeInFlightIDs.insert(itemId)
        defer { likeInFlightIDs.remove(itemId) }

        let previous = feedItems[index]
        let optimisticLiked = !previous.viewerHasLiked
        let optimisticCount = max(0, previous.likeCount + (optimisticLiked ? 1 : -1))
        feedItems[index] = previous.withLikeState(liked: optimisticLiked, likeCount: optimisticCount)
        feedState = .loaded(feedItems)

        do {
            let result: LikeStateModel
            if optimisticLiked {
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
            if let updatedIndex = feedItems.firstIndex(where: { $0.id == itemId }) {
                feedItems[updatedIndex] = feedItems[updatedIndex].withLikeState(
                    liked: result.liked,
                    likeCount: result.likeCount
                )
                feedState = .loaded(feedItems)
            }
        } catch {
            if let revertIndex = feedItems.firstIndex(where: { $0.id == itemId }) {
                feedItems[revertIndex] = previous
                feedState = .loaded(feedItems)
            }
            likeErrorMessage = error.localizedDescription
        }
    }

    func loadMoreFeedIfNeeded(currentItem item: FeedItemModel) async {
        guard canLoadMoreFeed,
              let index = feedItems.firstIndex(where: { $0.id == item.id }),
              index >= feedItems.count - 4
        else {
            return
        }
        await loadFeed(reset: false)
    }

    private func loadPrompt() async {
        let hideStale = shouldHideCachedPromptWhileRefreshing()
        if let cached = cachedPrompt, !hideStale {
            promptState = .loaded(cached)
        } else if hideStale || cachedPrompt == nil {
            promptState = .loading
        }

        guard networkMonitor.isOnline else {
            if let cachedPrompt {
                promptState = .loaded(cachedPrompt)
            } else if loadedPrompt == nil {
                promptState = .failed("Couldn’t load today’s prompt while offline.")
            }
            return
        }

        do {
            let prompt = try await promptFetcher.fetchTodaysPrompt()
            cachedPrompt = prompt
            lastPromptSyncedAt = dateProvider.now()
            promptState = .loaded(prompt)
            persistHomeCache()
        } catch let error as PromptAPIError where error == .promptNotFound {
            cachedPrompt = nil
            lastPromptSyncedAt = dateProvider.now()
            promptState = .missing
            persistHomeCache()
        } catch {
            if let cachedPrompt {
                promptState = .loaded(cachedPrompt)
            } else if loadedPrompt == nil {
                promptState = .failed(error.localizedDescription)
            }
        }
    }

    private func loadFeed(reset: Bool) async {
        if reset && feedItems.isEmpty {
            feedState = .loading
        }
        if reset {
            isLoadingMoreFeed = false
        } else {
            isLoadingMoreFeed = true
        }

        guard networkMonitor.isOnline else {
            if feedItems.isEmpty {
                feedState = .failed("Couldn’t load community stories while offline.")
            }
            isLoadingMoreFeed = false
            return
        }

        let cursor = reset ? nil : nextFeedCursor
        do {
            let page = try await feedFetcher.fetchRecentFeed(
                accessToken: accessTokenProvider(),
                cursor: cursor,
                limit: feedPageSize,
                creativeType: ProductConfig.current.creativeTypeID
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
            persistHomeCache()
        } catch {
            if reset && feedItems.isEmpty {
                feedState = .failed(
                    "Couldn’t load community stories. Check your connection and try again."
                )
            }
        }
        isLoadingMoreFeed = false
    }

    private func restoreCachedHomeSnapshot() {
        guard let snapshot = try? homeCacheStore.load() else { return }
        cachedPrompt = snapshot.prompt
        lastPromptSyncedAt = snapshot.cachedAt
        if let prompt = snapshot.prompt {
            let hideStale = PromptFreshness.shouldHideCachedPrompt(
                cachedAt: snapshot.cachedAt,
                promptDate: prompt.promptDate,
                now: dateProvider.now()
            )
            if hideStale && networkMonitor.isOnline {
                promptState = .loading
            } else {
                promptState = .loaded(prompt)
            }
        }
        feedItems = snapshot.feedItems
        nextFeedCursor = snapshot.nextFeedCursor
        if !feedItems.isEmpty {
            feedState = .loaded(feedItems)
        }
    }

    private func persistHomeCache() {
        let snapshot = CachedHomeSnapshot(
            prompt: cachedPrompt,
            feedItems: feedItems,
            nextFeedCursor: nextFeedCursor,
            cachedAt: lastPromptSyncedAt ?? dateProvider.now()
        )
        try? homeCacheStore.save(snapshot)
    }

    private func shouldHideCachedPromptWhileRefreshing() -> Bool {
        guard networkMonitor.isOnline else { return false }
        guard let lastPromptSyncedAt else { return cachedPrompt != nil }
        return PromptFreshness.shouldHideCachedPrompt(
            cachedAt: lastPromptSyncedAt,
            promptDate: cachedPrompt?.promptDate,
            now: dateProvider.now()
        )
    }
}
