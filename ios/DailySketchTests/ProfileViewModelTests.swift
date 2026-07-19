import XCTest
@testable import DailySketch

@MainActor
final class ProfileViewModelTests: XCTestCase {
    func testLoadOwnProfileEmptyGallery() async {
        let fetcher = RecordingProfileFetcher()
        fetcher.profile = PublicProfileModel(
            id: UUID(),
            username: "matt",
            displayName: "Matt",
            bio: "Hello",
            avatarURL: nil,
            submissionCount: 0,
            currentStreak: 0,
            isSelf: true
        )
        fetcher.pages = [RecentFeedPage(items: [], nextCursor: nil)]

        let model = ProfileViewModel(
            mode: .own,
            profileFetcher: fetcher,
            accessTokenProvider: { "token" },
            ownUsernameProvider: { "matt" }
        )
        await model.load()

        XCTAssertEqual(model.contentState, .empty)
        XCTAssertEqual(model.profile?.username, "matt")
        XCTAssertTrue(model.showsOwnControls)
        XCTAssertEqual(model.streakLabel, "0-day streak")
        XCTAssertEqual(fetcher.fetchProfileCallCount, 1)
        XCTAssertEqual(fetcher.fetchSubmissionsCallCount, 1)
    }

    func testLoadOtherProfilePaginatedGallery() async {
        let first = FeedItemModel.preview
        let second = FeedItemModel(
            id: UUID(),
            imageURL: URL(string: "https://example.test/display-2")!,
            thumbnailURL: URL(string: "https://example.test/thumb-2")!,
            userId: first.userId,
            username: "other",
            displayName: "Other",
            avatarURL: nil,
            promptWords: ["A", "B", "C"],
            promptDate: Date(),
            timerMode: "no_timer",
            timerSeconds: nil,
            captionPreview: nil,
            likeCount: 1,
            reflectionCount: 0,
            viewerHasLiked: false,
            isOwner: false,
            publishedAt: Date()
        )
        let fetcher = RecordingProfileFetcher()
        fetcher.profile = PublicProfileModel(
            id: UUID(),
            username: "other",
            displayName: "Other",
            bio: nil,
            avatarURL: nil,
            submissionCount: 2,
            currentStreak: 4,
            isSelf: false
        )
        fetcher.pages = [
            RecentFeedPage(items: [first], nextCursor: "cursor-1"),
            RecentFeedPage(items: [second], nextCursor: nil),
        ]

        let model = ProfileViewModel(
            mode: .other(username: "other"),
            profileFetcher: fetcher,
            accessTokenProvider: { nil },
            ownUsernameProvider: { nil }
        )
        await model.load()
        XCTAssertEqual(model.contentState, .loaded)
        XCTAssertEqual(model.galleryItems.count, 1)
        XCTAssertEqual(model.streakLabel, "4-day streak")
        XCTAssertFalse(model.showsOwnControls)

        await model.loadMoreIfNeeded(currentItem: first)
        XCTAssertEqual(model.galleryItems.count, 2)
        XCTAssertEqual(fetcher.lastCursor, "cursor-1")
    }

    func testLoadFailureSurfacesMessage() async {
        let fetcher = RecordingProfileFetcher()
        fetcher.error = ProfileAPIError.underlying("gone")
        let model = ProfileViewModel(
            mode: .other(username: "missing"),
            profileFetcher: fetcher
        )
        await model.load()
        XCTAssertEqual(model.contentState, .failed("gone"))
    }
}
