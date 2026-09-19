import Foundation
@testable import DailySketch

/// Shared fixtures so tests build flows and published models the same way
/// the Daily Sketch module does, without repeating its wiring.
@MainActor
enum TestFixtures {
    static let module = SketchModule()

    static func guestProfile() -> CurrentUserProfile {
        CurrentUserProfile(
            id: UUID(),
            username: nil,
            displayName: "Guest",
            profileCompleted: false,
            status: "incomplete"
        )
    }

    static func makeAuth(profile: CurrentUserProfile = guestProfile()) -> AuthSessionStore {
        AuthSessionStore(
            authService: MockAuthService(),
            meFetcher: RecordingMeFetcher(profile: profile)
        )
    }

    static func makeCaptureFlow(
        auth: AuthSessionStore? = nil,
        profile: CurrentUserProfile = guestProfile(),
        guestStore: any GuestTimerPreferenceStoring = InMemoryGuestTimerPreferenceStore(),
        activeStore: any ActiveSessionStoring = InMemoryActiveSessionStore(),
        sessionService: any CreativeSessionServing = RecordingCreativeSessionRepository(),
        draftStore: any DraftStoring = InMemoryDraftStore(),
        imageStore: any DraftImageStoring = InMemoryDraftImageStore(),
        camera: any CameraAuthorizing = FakeCameraAuthorizer(),
        uploadService: (any UploadServing)? = nil,
        submissionService: (any SubmissionServing)? = nil,
        directUploader: (any DirectUploadTransporting)? = nil,
        publishedStore: (any PublishedSubmissionStoring)? = nil,
        analytics: (any AnalyticsTracking)? = nil
    ) -> CaptureFlowViewModel {
        CaptureFlowViewModel(
            creativeType: module.creativeTypeID,
            sessionLabels: module.sessionLabels,
            defaultTimerOption: module.defaultTimerOption,
            contentBuilder: { uploadId, caption in .sketch(uploadId: uploadId, caption: caption) },
            auth: auth ?? makeAuth(profile: profile),
            preferencesService: RecordingMeFetcher(profile: profile),
            guestTimerStore: guestStore,
            activeSessionStore: activeStore,
            sessionService: sessionService,
            draftStore: draftStore,
            imageStore: imageStore,
            cameraAuthorizer: camera,
            uploadService: uploadService,
            submissionService: submissionService,
            directUploader: directUploader,
            publishedStore: publishedStore,
            analytics: analytics
        )
    }

    static func sketchContent(
        imageURL: URL = URL(string: "https://example.test/display")!,
        thumbnailURL: URL = URL(string: "https://example.test/thumb")!
    ) -> SubmissionContentModel {
        .sketch(SketchContentModel(imageURL: imageURL, thumbnailURL: thumbnailURL))
    }

    static func sketchSubmission(
        id: UUID = UUID(),
        caption: String? = nil,
        timerMode: String = "countdown",
        timerSeconds: Int? = 180,
        likeCount: Int = 0,
        reflectionCount: Int = 0,
        viewerHasLiked: Bool = false,
        isOwner: Bool = true,
        userId: UUID = UUID(),
        username: String = "sketchy",
        displayName: String = "Sketcher",
        promptWords: [String] = ["Chocolate", "Coffee", "Banana"],
        promptDate: Date = Date(timeIntervalSince1970: 1_784_332_800),
        sessionId: UUID = UUID(),
        publishedAt: Date = Date()
    ) -> SubmissionModel {
        SubmissionModel(
            id: id,
            creativeType: "sketch",
            caption: caption,
            content: sketchContent(),
            status: "published",
            timerMode: timerMode,
            timerSeconds: timerSeconds,
            likeCount: likeCount,
            reflectionCount: reflectionCount,
            viewerHasLiked: viewerHasLiked,
            isOwner: isOwner,
            userId: userId,
            username: username,
            displayName: displayName,
            promptWords: promptWords,
            promptDate: promptDate,
            sessionId: sessionId,
            publishedAt: publishedAt
        )
    }

    /// A feed item sharing prompt/timer/content with `base` but a different identity.
    static func feedItem(
        basedOn base: FeedItemModel = .preview,
        id: UUID = UUID(),
        username: String,
        displayName: String,
        captionPreview: String? = nil,
        likeCount: Int = 0,
        viewerHasLiked: Bool = false,
        isOwner: Bool = false,
        publishedAt: Date? = nil
    ) -> FeedItemModel {
        FeedItemModel(
            id: id,
            creativeType: base.creativeType,
            content: base.content,
            userId: base.userId,
            username: username,
            displayName: displayName,
            avatarURL: nil,
            promptWords: base.promptWords,
            promptDate: base.promptDate,
            timerMode: base.timerMode,
            timerSeconds: base.timerSeconds,
            captionPreview: captionPreview,
            likeCount: likeCount,
            reflectionCount: 0,
            viewerHasLiked: viewerHasLiked,
            isOwner: isOwner,
            publishedAt: publishedAt ?? base.publishedAt
        )
    }
}
