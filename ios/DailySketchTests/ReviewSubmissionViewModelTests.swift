import UIKit
import XCTest
@preconcurrency import DailyCreativeAPI
@testable import DailySketch

@MainActor
final class ReviewSubmissionViewModelTests: XCTestCase {
    private func makeDraft(
        imageStore: InMemoryDraftImageStore,
        caption: String? = "hello",
        serverSessionId: UUID? = UUID(),
        pendingPublication: Bool = false,
        publicationIdempotencyKey: String? = nil
    ) throws -> (LocalDraft, Data) {
        let data = makeJPEG()
        let fileName = try imageStore.write(data)
        let draft = LocalDraft(
            id: UUID(),
            localSessionId: UUID(),
            serverSessionId: serverSessionId,
            promptId: UUID(),
            promptWords: ["Chocolate", "Coffee", "Banana"],
            promptAccessibilityLabel: "Today’s prompt: Chocolate, Coffee, Banana.",
            promptDate: Date(timeIntervalSince1970: 1_784_332_800),
            timerMode: "countdown",
            selectedTimerSeconds: 300,
            sessionStartedAt: Date(),
            imageFileName: fileName,
            caption: caption,
            createdAt: Date(),
            updatedAt: Date(),
            pendingAuthentication: true,
            pendingPublication: pendingPublication,
            publicationIdempotencyKey: publicationIdempotencyKey
        )
        return (draft, data)
    }

    private func waitUntil(_ condition: @autoclosure () -> Bool, timeout: TimeInterval = 2) async {
        let deadline = Date().addingTimeInterval(timeout)
        while !condition(), Date() < deadline {
            await Task.yield()
        }
    }

    func testCaptionSurvivesImageReplacement() throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let (draft, data) = try makeDraft(imageStore: imageStore, caption: "keep this caption")
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            isAuthenticated: { false },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        model.caption = "keep this caption"

        let replacement = makeJPEG(color: .green)
        try model.replaceImage(with: replacement)

        XCTAssertEqual(model.caption, "keep this caption")
        XCTAssertEqual(try draftStore.list().first?.caption, "keep this caption")
        XCTAssertNotEqual(model.draft.imageFileName, draft.imageFileName)
    }

    func testGuestSubmitNeedsAuthenticationAndPreservesDraft() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let (draft, data) = try makeDraft(imageStore: imageStore)
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            isAuthenticated: { false },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.caption = "guest caption"
        model.submitToCommunity()
        await waitUntil(outcome != nil)

        XCTAssertEqual(outcome, .needsAuthentication)
        let saved = try draftStore.list().first
        XCTAssertEqual(saved?.caption, "guest caption")
        XCTAssertEqual(saved?.pendingAuthentication, true)
        XCTAssertEqual(saved?.pendingPublication, true)
    }

    func testPublishHappyPathDeletesViaOutcomeAndRecordsPublished() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let publishedStore = InMemoryPublishedSubmissionStore()
        let uploads = RecordingUploadRepository()
        let submissions = RecordingSubmissionRepository()
        let uploader = RecordingDirectUploader()
        let (draft, data) = try makeDraft(imageStore: imageStore, caption: "ship it")
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: uploads,
            submissionService: submissions,
            sessionService: RecordingSketchSessionRepository(),
            directUploader: uploader,
            publishedStore: publishedStore,
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.caption = "ship it"
        model.submitToCommunity()
        await waitUntil(outcome != nil)

        guard case .published(let submission) = outcome else {
            return XCTFail("Expected published outcome, got \(String(describing: outcome))")
        }
        XCTAssertEqual(uploads.createCallCount, 1)
        XCTAssertEqual(uploads.completeCallCount, 1)
        XCTAssertEqual(uploader.uploadCallCount, 1)
        XCTAssertEqual(submissions.createCallCount, 1)
        XCTAssertEqual(try publishedStore.list().map(\.id), [submission.id])
        XCTAssertNotNil(try draftStore.list().first?.publicationIdempotencyKey)
    }

    func testPublishFailurePreservesDraftAndCaption() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let uploads = RecordingUploadRepository()
        uploads.createError = PublicationAPIError.underlying("network down")
        let (draft, data) = try makeDraft(imageStore: imageStore, caption: "keep me")
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: uploads,
            submissionService: RecordingSubmissionRepository(),
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.caption = "keep me"
        model.submitToCommunity()
        await waitUntil(model.publishErrorMessage != nil)

        XCTAssertNil(outcome)
        XCTAssertEqual(model.publishErrorMessage, "network down")
        let saved = try draftStore.list().first
        XCTAssertEqual(saved?.caption, "keep me")
        XCTAssertEqual(saved?.pendingPublication, true)
    }

    func testDuplicateSafeRetryReusesIdempotencyKey() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let submissions = RecordingSubmissionRepository()
        submissions.createError = PublicationAPIError.underlying("temporary")
        let (draft, data) = try makeDraft(
            imageStore: imageStore,
            publicationIdempotencyKey: "fixed-key"
        )
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: RecordingUploadRepository(),
            submissionService: submissions,
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(model.publishErrorMessage != nil)

        submissions.createError = nil
        model.retryPublish()
        await waitUntil(submissions.createCallCount >= 2)

        XCTAssertEqual(submissions.lastIdempotencyKey, "fixed-key")
        XCTAssertEqual(try draftStore.list().first?.publicationIdempotencyKey, "fixed-key")
    }

    func testProfileIncompleteRoutesToCompletion() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let (draft, data) = try makeDraft(imageStore: imageStore)
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { false },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(outcome != nil)

        XCTAssertEqual(outcome, .needsProfileCompletion)
        XCTAssertEqual(try draftStore.list().first?.pendingPublication, true)
    }

    func testReopenUsesPersistedCaption() throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let (draft, data) = try makeDraft(imageStore: imageStore, caption: "reopened")
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            isAuthenticated: { false },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        XCTAssertEqual(model.caption, "reopened")
    }

    func testAuthExpiryDuringPublishRoutesToAuthentication() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let uploads = RecordingUploadRepository()
        uploads.createError = PublicationAPIError.sessionExpired
        let (draft, data) = try makeDraft(imageStore: imageStore)
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: uploads,
            submissionService: RecordingSubmissionRepository(),
            sessionService: RecordingSketchSessionRepository(),
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(outcome != nil)

        XCTAssertEqual(outcome, .needsAuthentication)
        XCTAssertEqual(try draftStore.list().first?.pendingPublication, true)
    }

    func testCompletedUploadSkipsReuploadOnRetry() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let uploads = RecordingUploadRepository()
        let submissions = RecordingSubmissionRepository()
        submissions.createError = PublicationAPIError.underlying("temporary")
        let uploadId = UUID()
        var (draft, data) = try makeDraft(imageStore: imageStore)
        draft.uploadId = uploadId
        draft.uploadCompleted = true
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: uploads,
            submissionService: submissions,
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(model.publishErrorMessage != nil)

        submissions.createError = nil
        model.retryPublish()
        await waitUntil(submissions.createCallCount >= 2)

        XCTAssertEqual(uploads.createCallCount, 0)
        XCTAssertEqual(submissions.createCallCount, 2)
    }

    func testSignedUploadExpiryRequestsFreshSlotOnRetry() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let uploads = RecordingUploadRepository()
        let uploader = RecordingDirectUploader()
        uploader.uploadError = PublicationAPIError.signedUploadExpired
        let (draft, data) = try makeDraft(imageStore: imageStore)
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: uploads,
            submissionService: RecordingSubmissionRepository(),
            directUploader: uploader,
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(model.publishErrorMessage != nil)

        XCTAssertEqual(model.publishErrorMessage, PublicationAPIError.signedUploadExpired.localizedDescription)
        uploader.uploadError = nil
        model.retryPublish()
        await waitUntil(uploads.createCallCount >= 2)

        XCTAssertGreaterThanOrEqual(uploads.createCallCount, 2)
    }

    func testPublishSendsDraftPromptId() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let submissions = RecordingSubmissionRepository()
        let (draft, data) = try makeDraft(imageStore: imageStore, caption: "prompt check")
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: RecordingUploadRepository(),
            submissionService: submissions,
            sessionService: RecordingSketchSessionRepository(),
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(outcome != nil)

        XCTAssertEqual(submissions.lastPromptId, draft.promptId)
        XCTAssertEqual(submissions.lastSessionId, draft.serverSessionId)
    }

    func testLazySessionCreateSendsClientStartedAt() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let sessions = RecordingSketchSessionRepository()
        let startedAt = Date(timeIntervalSince1970: 1_784_300_000)
        let (baseDraft, data) = try makeDraft(imageStore: imageStore, serverSessionId: nil)
        let draft = LocalDraft(
            id: baseDraft.id,
            localSessionId: baseDraft.localSessionId,
            serverSessionId: nil,
            promptId: baseDraft.promptId,
            promptWords: baseDraft.promptWords,
            promptAccessibilityLabel: baseDraft.promptAccessibilityLabel,
            promptDate: baseDraft.promptDate,
            timerMode: baseDraft.timerMode,
            selectedTimerSeconds: baseDraft.selectedTimerSeconds,
            sessionStartedAt: startedAt,
            imageFileName: baseDraft.imageFileName,
            caption: baseDraft.caption,
            createdAt: baseDraft.createdAt,
            updatedAt: baseDraft.updatedAt,
            pendingAuthentication: false,
            pendingPublication: false
        )
        try draftStore.save(draft)

        var outcome: ReviewSubmissionOutcome?
        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: RecordingUploadRepository(),
            submissionService: RecordingSubmissionRepository(),
            sessionService: sessions,
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { outcome = $0 },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(outcome != nil)

        XCTAssertEqual(sessions.createCallCount, 1)
        XCTAssertEqual(sessions.lastClientStartedAt, startedAt)
    }

    func testPromptDateOutOfWindowBlocksRetry() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let submissions = RecordingSubmissionRepository()
        submissions.createError = PublicationAPIError.promptDateOutOfWindow
        let (draft, data) = try makeDraft(imageStore: imageStore)
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            uploadService: RecordingUploadRepository(),
            submissionService: submissions,
            sessionService: RecordingSketchSessionRepository(),
            directUploader: RecordingDirectUploader(),
            accessTokenProvider: { "token" },
            isAuthenticated: { true },
            canPublish: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        model.submitToCommunity()
        await waitUntil(model.isPublishBlocked)

        XCTAssertTrue(model.isPublishBlocked)
        XCTAssertEqual(
            model.publishErrorMessage,
            PublicationAPIError.promptDateOutOfWindow.localizedDescription
        )
        XCTAssertEqual(try draftStore.list().first?.pendingPublication, false)

        let callsBeforeRetry = submissions.createCallCount
        model.retryPublish()
        await Task.yield()
        XCTAssertEqual(submissions.createCallCount, callsBeforeRetry)
    }

    func testPublicationAPIErrorMappingForNewCodes() {
        func envelope(_ code: String) -> Data {
            Data(#"{"error":{"code":"\#(code)","message":"x"}}"#.utf8)
        }

        XCTAssertEqual(
            mapAPIError(ErrorResponse.error(422, envelope("prompt_date_out_of_window"), nil, NSError(domain: "t", code: 0))) as? PublicationAPIError,
            .promptDateOutOfWindow
        )
        XCTAssertEqual(
            mapAPIError(ErrorResponse.error(409, envelope("prompt_mismatch"), nil, NSError(domain: "t", code: 0))) as? PublicationAPIError,
            .promptMismatch
        )
        XCTAssertEqual(
            mapAPIError(ErrorResponse.error(422, envelope("invalid_session_transition"), nil, NSError(domain: "t", code: 0))) as? PublicationAPIError,
            .invalidSessionTransition
        )
        XCTAssertEqual(
            mapAPIError(ErrorResponse.error(404, envelope("prompt_not_found"), nil, NSError(domain: "t", code: 0))) as? PublicationAPIError,
            .promptNotFound
        )
    }

    private func makeJPEG(color: UIColor = .red) -> Data {
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 6, height: 6))
        let image = renderer.image { context in
            color.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 6, height: 6))
        }
        return image.jpegData(compressionQuality: 0.9)!
    }
}
