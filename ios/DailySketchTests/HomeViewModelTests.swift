import XCTest
@testable import DailySketch

@MainActor
final class HomeViewModelTests: XCTestCase {
    private func samplePrompt(
        words: (String, String, String) = ("Chocolate", "Coffee", "Banana")
    ) -> DailyPromptModel {
        DailyPromptModel(
            id: UUID(uuidString: "a1b2c3d4-e5f6-7890-abcd-ef1234567890")!,
            promptDate: Date(timeIntervalSince1970: 1_784_332_800),
            word1: words.0,
            word2: words.1,
            word3: words.2,
            status: "published",
            publishedAt: Date(timeIntervalSince1970: 1_784_246_400)
        )
    }

    private func makeSketchFlow() -> SketchFlowViewModel {
        let auth = AuthSessionStore(
            authService: MockAuthService(),
            meFetcher: RecordingMeFetcher(
                profile: CurrentUserProfile(
                    id: UUID(),
                    username: nil,
                    displayName: "Guest",
                    profileCompleted: false,
                    status: "incomplete"
                )
            )
        )
        return SketchFlowViewModel(
            auth: auth,
            preferencesService: RecordingMeFetcher(
                profile: CurrentUserProfile(
                    id: UUID(),
                    username: nil,
                    displayName: "Guest",
                    profileCompleted: false,
                    status: "incomplete"
                )
            ),
            guestTimerStore: InMemoryGuestTimerPreferenceStore(),
            activeSessionStore: InMemoryActiveSessionStore(),
            sessionService: RecordingSketchSessionRepository(),
            draftStore: InMemoryDraftStore(),
            imageStore: InMemoryDraftImageStore(),
            cameraAuthorizer: FakeCameraAuthorizer()
        )
    }

    private func makeModel(
        fetcher: RecordingPromptFetcher,
        publishedStore: any PublishedSubmissionStoring = InMemoryPublishedSubmissionStore(),
        socialService: any SocialServing = RecordingSocialRepository(),
        homeCacheStore: any HomeCacheStoring = InMemoryHomeCacheStore(),
        networkMonitor: any NetworkMonitoring = FixedNetworkMonitor(isOnline: true),
        dateProvider: any DateProviding = SystemDateProvider(),
        isAuthenticated: @escaping () -> Bool = { false },
        accessTokenProvider: @escaping () -> String? = { nil }
    ) -> HomeViewModel {
        HomeViewModel(
            promptFetcher: fetcher,
            feedFetcher: fetcher,
            socialService: socialService,
            publishedStore: publishedStore,
            homeCacheStore: homeCacheStore,
            networkMonitor: networkMonitor,
            analytics: InMemoryAnalyticsClient(),
            sketchFlow: makeSketchFlow(),
            dateProvider: dateProvider,
            isAuthenticated: isAuthenticated,
            accessTokenProvider: accessTokenProvider
        )
    }

    func testLoadRendersThreeWordsInOrder() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let model = makeModel(fetcher: fetcher)

        await model.load()

        guard case .loaded(let prompt) = model.promptState else {
            return XCTFail("Expected loaded prompt")
        }
        XCTAssertEqual(prompt.words, ["Chocolate", "Coffee", "Banana"])
        XCTAssertTrue(model.canStartSketch)
        XCTAssertEqual(model.feedState, .empty)
    }

    func testFeedFailureDoesNotBlockPromptOrStartSketch() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        fetcher.feedError = PromptAPIError.underlying("network down")
        let model = makeModel(fetcher: fetcher)

        await model.load()

        XCTAssertEqual(fetcher.todaysPromptCallCount, 1)
        XCTAssertEqual(fetcher.recentFeedCallCount, 1)
        guard case .loaded = model.promptState else {
            return XCTFail("Prompt should remain usable when feed fails")
        }
        XCTAssertTrue(model.canStartSketch)
        guard case .failed = model.feedState else {
            return XCTFail("Expected feed failure state")
        }
    }

    func testPromptFailureDoesNotBlockFeed() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.promptError = PromptAPIError.underlying("timeout")
        fetcher.feed = RecentFeedPage(items: [], nextCursor: nil)
        let model = makeModel(fetcher: fetcher)

        await model.load()

        guard case .failed = model.promptState else {
            return XCTFail("Expected prompt failure")
        }
        XCTAssertFalse(model.canStartSketch)
        XCTAssertEqual(model.feedState, .empty)
    }

    func testMissingPromptIsRecoverableWithoutInventingLocalPrompt() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.promptError = PromptAPIError.promptNotFound
        let model = makeModel(fetcher: fetcher)

        await model.load()

        XCTAssertEqual(model.promptState, .missing)
        XCTAssertNil(model.cachedPrompt)
        XCTAssertNil(model.promptWords)
        XCTAssertFalse(model.canStartSketch)
        XCTAssertEqual(model.feedState, .empty)
    }

    func testEmptyFeedState() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        fetcher.feed = RecentFeedPage(items: [], nextCursor: nil)
        let model = makeModel(fetcher: fetcher)

        await model.load()

        XCTAssertEqual(model.feedState, .empty)
    }

    func testStartSketchOpensTimerSelectionByDefault() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let model = makeModel(fetcher: fetcher)

        await model.load()
        model.startSketch()
        // startSketch kicks an async Task — wait briefly for sheet flag.
        let deadline = Date().addingTimeInterval(1)
        while !model.sketchFlow.showsTimerSelection, Date() < deadline {
            await Task.yield()
        }

        XCTAssertTrue(model.sketchFlow.showsTimerSelection)
        XCTAssertFalse(model.sketchFlow.showsActiveSession)
    }

    func testCachedPromptSurvivesTransientRefreshFailure() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let model = makeModel(fetcher: fetcher)

        await model.load()
        fetcher.promptError = PromptAPIError.underlying("temporary")
        await model.retryPrompt()

        guard case .loaded(let prompt) = model.promptState else {
            return XCTFail("Cached prompt should remain visible")
        }
        XCTAssertEqual(prompt.word1, "Chocolate")
        XCTAssertNotNil(model.cachedPrompt)
    }

    func testHomeCompletionStateAfterLocalPublication() async throws {
        let fetcher = RecordingPromptFetcher()
        let prompt = samplePrompt()
        fetcher.prompt = prompt
        let publishedStore = InMemoryPublishedSubmissionStore()
        try publishedStore.save(
            PublishedLocalSubmission(
                id: UUID(),
                promptId: prompt.id,
                promptDate: prompt.promptDate,
                timerMode: "countdown",
                selectedTimerSeconds: 300,
                caption: "done",
                publishedAt: Date()
            )
        )
        let model = makeModel(fetcher: fetcher, publishedStore: publishedStore)

        await model.load()

        XCTAssertTrue(model.hasSketchedToday)
        XCTAssertEqual(model.primarySketchButtonTitle, "Create Another Sketch")
        XCTAssertEqual(model.viewMySketchTitle, "View My Sketch")
        XCTAssertEqual(model.todaysPublished.count, 1)
        XCTAssertTrue(model.canStartSketch)
    }

    func testHomeCompletionPluralizesViewTitle() async throws {
        let fetcher = RecordingPromptFetcher()
        let prompt = samplePrompt()
        fetcher.prompt = prompt
        let publishedStore = InMemoryPublishedSubmissionStore()
        for _ in 0..<2 {
            try publishedStore.save(
                PublishedLocalSubmission(
                    id: UUID(),
                    promptId: prompt.id,
                    promptDate: prompt.promptDate,
                    timerMode: "no_timer",
                    selectedTimerSeconds: nil,
                    caption: nil,
                    publishedAt: Date()
                )
            )
        }
        let model = makeModel(fetcher: fetcher, publishedStore: publishedStore)
        await model.load()
        XCTAssertEqual(model.viewMySketchTitle, "View My Sketches")
    }

    func testLoadedFeedStateMapsItems() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let item = FeedItemModel.preview
        fetcher.feed = RecentFeedPage(items: [item], nextCursor: "cursor-1")
        let model = makeModel(fetcher: fetcher)

        await model.load()

        guard case .loaded(let items) = model.feedState else {
            return XCTFail("Expected loaded feed")
        }
        XCTAssertEqual(items.count, 1)
        XCTAssertEqual(items.first?.id, item.id)
        XCTAssertEqual(model.nextFeedCursor, "cursor-1")
        XCTAssertEqual(fetcher.lastFeedLimit, 20)
        XCTAssertNil(fetcher.lastFeedCursor)
    }

    func testInfiniteScrollAppendsNextPage() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let first = FeedItemModel.preview
        let second = FeedItemModel(
            id: UUID(),
            creativeType: "sketch",
            imageURL: first.imageURL,
            thumbnailURL: first.thumbnailURL,
            userId: first.userId,
            username: "second",
            displayName: "Second",
            avatarURL: nil,
            promptWords: first.promptWords,
            promptDate: first.promptDate,
            timerMode: first.timerMode,
            timerSeconds: first.timerSeconds,
            captionPreview: "Next page",
            bodyPreview: nil,
            wordCount: nil,
            likeCount: 1,
            reflectionCount: 0,
            viewerHasLiked: false,
            isOwner: false,
            publishedAt: first.publishedAt.addingTimeInterval(-3_600)
        )
        fetcher.feedPages[nil] = RecentFeedPage(items: [first], nextCursor: "page-2")
        fetcher.feedPages["page-2"] = RecentFeedPage(items: [second], nextCursor: nil)
        let model = makeModel(fetcher: fetcher)

        await model.load()
        await model.loadMoreFeedIfNeeded(currentItem: first)

        guard case .loaded(let items) = model.feedState else {
            return XCTFail("Expected loaded feed after pagination")
        }
        XCTAssertEqual(items.map(\.id), [first.id, second.id])
        XCTAssertNil(model.nextFeedCursor)
        XCTAssertEqual(fetcher.recentFeedCallCount, 2)
        XCTAssertEqual(fetcher.lastFeedCursor, "page-2")
    }

    func testRefreshReplacesFeedItems() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let first = FeedItemModel.preview
        fetcher.feed = RecentFeedPage(items: [first], nextCursor: nil)
        let model = makeModel(fetcher: fetcher)
        await model.load()

        let refreshed = FeedItemModel(
            id: UUID(),
            creativeType: "sketch",
            imageURL: first.imageURL,
            thumbnailURL: first.thumbnailURL,
            userId: first.userId,
            username: "refreshed",
            displayName: "Refreshed",
            avatarURL: nil,
            promptWords: first.promptWords,
            promptDate: first.promptDate,
            timerMode: first.timerMode,
            timerSeconds: first.timerSeconds,
            captionPreview: nil,
            bodyPreview: nil,
            wordCount: nil,
            likeCount: 0,
            reflectionCount: 0,
            viewerHasLiked: false,
            isOwner: false,
            publishedAt: Date()
        )
        fetcher.feed = RecentFeedPage(items: [refreshed], nextCursor: nil)
        await model.refresh()

        guard case .loaded(let items) = model.feedState else {
            return XCTFail("Expected loaded feed after refresh")
        }
        XCTAssertEqual(items.map(\.id), [refreshed.id])
    }

    func testRemoveFeedItemFallsBackToEmpty() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let item = FeedItemModel.preview
        fetcher.feed = RecentFeedPage(items: [item], nextCursor: nil)
        let model = makeModel(fetcher: fetcher)
        await model.load()

        model.removeFeedItem(id: item.id)

        XCTAssertEqual(model.feedState, .empty)
        XCTAssertTrue(model.feedItems.isEmpty)
    }

    func testOptimisticFeedLikeRollsBackOnFailure() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let item = FeedItemModel.preview
        fetcher.feed = RecentFeedPage(items: [item], nextCursor: nil)
        let social = RecordingSocialRepository()
        social.likeError = SocialAPIError.underlying("network")
        let model = makeModel(
            fetcher: fetcher,
            socialService: social,
            isAuthenticated: { true },
            accessTokenProvider: { "token" }
        )
        await model.load()

        await model.toggleLike(itemId: item.id)

        XCTAssertEqual(social.likeCallCount, 1)
        XCTAssertEqual(model.feedItems.first?.viewerHasLiked, false)
        XCTAssertEqual(model.feedItems.first?.likeCount, item.likeCount)
        XCTAssertEqual(model.likeErrorMessage, "network")
    }

    func testGuestFeedLikeTriggersAuthThenResumes() async {
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let item = FeedItemModel.preview
        fetcher.feed = RecentFeedPage(items: [item], nextCursor: nil)
        let social = RecordingSocialRepository()
        social.nextLikeState = LikeStateModel(liked: true, likeCount: 1)
        var authenticated = false
        let model = makeModel(
            fetcher: fetcher,
            socialService: social,
            isAuthenticated: { authenticated },
            accessTokenProvider: { authenticated ? "token" : nil }
        )
        await model.load()

        await model.toggleLike(itemId: item.id)
        XCTAssertEqual(social.likeCallCount, 0)
        XCTAssertEqual(model.pendingLikeSubmissionId, item.id)
        XCTAssertTrue(model.showsAuthSheet)

        authenticated = true
        await model.handleAuthenticationCompleted()

        XCTAssertEqual(social.likeCallCount, 1)
        XCTAssertTrue(model.feedItems.first?.viewerHasLiked == true)
        XCTAssertEqual(model.feedItems.first?.likeCount, 1)
        XCTAssertNil(model.pendingLikeSubmissionId)
    }

    func testRelativeTimestampFormatter() {
        let now = Date()
        XCTAssertEqual(
            RelativeTimestampFormatter.string(from: now.addingTimeInterval(-30), now: now),
            "just now"
        )
        XCTAssertEqual(
            RelativeTimestampFormatter.string(from: now.addingTimeInterval(-120), now: now),
            "2m ago"
        )
        XCTAssertEqual(
            RelativeTimestampFormatter.string(from: now.addingTimeInterval(-7_200), now: now),
            "2h ago"
        )
    }

    func testFreshCacheShowsWordsImmediately() throws {
        let now = Date(timeIntervalSince1970: 1_784_376_000)
        let clock = ControllableDateProvider(now: now)
        let cache = InMemoryHomeCacheStore()
        try cache.save(
            CachedHomeSnapshot(
                prompt: samplePrompt(),
                feedItems: [],
                nextFeedCursor: nil,
                cachedAt: now.addingTimeInterval(-5 * 60)
            )
        )
        let model = makeModel(
            fetcher: RecordingPromptFetcher(),
            homeCacheStore: cache,
            dateProvider: clock
        )

        guard case .loaded(let prompt) = model.promptState else {
            return XCTFail("Fresh cache should show words immediately")
        }
        XCTAssertEqual(prompt.words, ["Chocolate", "Coffee", "Banana"])
        XCTAssertTrue(model.canStartSketch)
    }

    func testStaleCacheHidesWordsUntilRefresh() async throws {
        let now = Date(timeIntervalSince1970: 1_784_376_000)
        let clock = ControllableDateProvider(now: now)
        let cache = InMemoryHomeCacheStore()
        try cache.save(
            CachedHomeSnapshot(
                prompt: samplePrompt(),
                feedItems: [],
                nextFeedCursor: nil,
                cachedAt: now.addingTimeInterval(-16 * 60)
            )
        )
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt(words: ("Moon", "River", "Lantern"))
        let model = makeModel(
            fetcher: fetcher,
            homeCacheStore: cache,
            dateProvider: clock
        )

        XCTAssertEqual(model.promptState, .loading)
        XCTAssertFalse(model.canStartSketch)
        XCTAssertEqual(model.cachedPrompt?.word1, "Chocolate")

        await model.load()

        guard case .loaded(let prompt) = model.promptState else {
            return XCTFail("Expected refreshed prompt")
        }
        XCTAssertEqual(prompt.words, ["Moon", "River", "Lantern"])
        XCTAssertEqual(fetcher.todaysPromptCallCount, 1)
    }

    func testUTCDayBoundaryHidesCachedWords() throws {
        // 23:50 UTC on day D, cache written; now is 00:10 UTC next day.
        let cachedAt = Date(timeIntervalSince1970: 1_784_332_800 - 10 * 60)
        let now = Date(timeIntervalSince1970: 1_784_332_800 + 10 * 60)
        let clock = ControllableDateProvider(now: now)
        let cache = InMemoryHomeCacheStore()
        try cache.save(
            CachedHomeSnapshot(
                prompt: samplePrompt(),
                feedItems: [],
                nextFeedCursor: nil,
                cachedAt: cachedAt
            )
        )
        let model = makeModel(
            fetcher: RecordingPromptFetcher(),
            homeCacheStore: cache,
            dateProvider: clock
        )

        XCTAssertEqual(model.promptState, .loading)
        XCTAssertFalse(model.canStartSketch)
    }

    func testOfflineKeepsStaleCachedWords() throws {
        let now = Date(timeIntervalSince1970: 1_784_376_000)
        let clock = ControllableDateProvider(now: now)
        let cache = InMemoryHomeCacheStore()
        try cache.save(
            CachedHomeSnapshot(
                prompt: samplePrompt(),
                feedItems: [],
                nextFeedCursor: nil,
                cachedAt: now.addingTimeInterval(-60 * 60)
            )
        )
        let model = makeModel(
            fetcher: RecordingPromptFetcher(),
            homeCacheStore: cache,
            networkMonitor: FixedNetworkMonitor(isOnline: false),
            dateProvider: clock
        )

        guard case .loaded(let prompt) = model.promptState else {
            return XCTFail("Offline should keep showing cached inspiration")
        }
        XCTAssertEqual(prompt.word1, "Chocolate")
        XCTAssertTrue(model.canStartSketch)
    }

    func testForegroundResumeHidesStaleWordsAndRefreshes() async {
        let clock = ControllableDateProvider(now: Date(timeIntervalSince1970: 1_784_376_000))
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let model = makeModel(fetcher: fetcher, dateProvider: clock)

        await model.load()
        XCTAssertEqual(fetcher.todaysPromptCallCount, 1)
        guard case .loaded = model.promptState else {
            return XCTFail("Expected loaded prompt after initial load")
        }

        clock.advance(by: 16 * 60)
        fetcher.prompt = samplePrompt(words: ("Oak", "Ink", "Sky"))

        await model.handleSceneBecameActive()

        guard case .loaded(let prompt) = model.promptState else {
            return XCTFail("Expected refreshed prompt after foreground")
        }
        XCTAssertEqual(prompt.words, ["Oak", "Ink", "Sky"])
        XCTAssertEqual(fetcher.todaysPromptCallCount, 2)
    }

    func testForegroundResumeSkipsFreshPrompt() async {
        let clock = ControllableDateProvider(now: Date(timeIntervalSince1970: 1_784_376_000))
        let fetcher = RecordingPromptFetcher()
        fetcher.prompt = samplePrompt()
        let model = makeModel(fetcher: fetcher, dateProvider: clock)

        await model.load()
        clock.advance(by: 5 * 60)
        await model.handleSceneBecameActive()

        XCTAssertEqual(fetcher.todaysPromptCallCount, 1)
    }

    func testPromptFreshnessRules() {
        let now = Date(timeIntervalSince1970: 1_784_376_000)
        XCTAssertFalse(
            PromptFreshness.shouldHideCachedPrompt(
                cachedAt: now.addingTimeInterval(-5 * 60),
                promptDate: now,
                now: now
            )
        )
        XCTAssertTrue(
            PromptFreshness.shouldHideCachedPrompt(
                cachedAt: now.addingTimeInterval(-15 * 60),
                promptDate: now,
                now: now
            )
        )
        let beforeMidnight = Date(timeIntervalSince1970: 1_784_332_800 - 60)
        let afterMidnight = Date(timeIntervalSince1970: 1_784_332_800 + 60)
        XCTAssertTrue(
            PromptFreshness.shouldHideCachedPrompt(
                cachedAt: beforeMidnight,
                promptDate: beforeMidnight,
                now: afterMidnight
            )
        )
    }

    func testPromptDateFormattingUsesOrdinalDay() {
        // 2026-07-18 UTC
        let eighteenth = Date(timeIntervalSince1970: 1_784_332_800)
        XCTAssertEqual(PromptDateFormatting.ordinalDayMonthYear(eighteenth), "18th July 2026")
        XCTAssertEqual(
            PromptDateFormatting.inspirationTitle(for: eighteenth),
            "Inspiration for 18th July 2026"
        )
        XCTAssertEqual(samplePrompt().inspirationTitle, "Inspiration for 18th July 2026")

        // 2026-07-31 UTC
        let thirtyFirst = Date(timeIntervalSince1970: 1_785_456_000)
        XCTAssertEqual(PromptDateFormatting.ordinalDayMonthYear(thirtyFirst), "31st July 2026")

        // 2026-07-01 UTC
        let first = Date(timeIntervalSince1970: 1_782_864_000)
        XCTAssertEqual(PromptDateFormatting.ordinalDayMonthYear(first), "1st July 2026")

        // 2026-07-02 UTC
        let second = Date(timeIntervalSince1970: 1_782_950_400)
        XCTAssertEqual(PromptDateFormatting.ordinalDayMonthYear(second), "2nd July 2026")

        // 2026-07-03 UTC
        let third = Date(timeIntervalSince1970: 1_783_036_800)
        XCTAssertEqual(PromptDateFormatting.ordinalDayMonthYear(third), "3rd July 2026")

        // 2026-07-11 UTC (teen exception)
        let eleventh = Date(timeIntervalSince1970: 1_783_728_000)
        XCTAssertEqual(PromptDateFormatting.ordinalDayMonthYear(eleventh), "11th July 2026")
    }
}
