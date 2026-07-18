import UIKit
import XCTest
@testable import DailySketch

@MainActor
final class ReviewSubmissionViewModelTests: XCTestCase {
    private func makeDraft(imageStore: InMemoryDraftImageStore, caption: String? = "hello") throws -> (LocalDraft, Data) {
        let data = makeJPEG()
        let fileName = try imageStore.write(data)
        let draft = LocalDraft(
            id: UUID(),
            localSessionId: UUID(),
            serverSessionId: nil,
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
            pendingPublication: false
        )
        return (draft, data)
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

        let deadline = Date().addingTimeInterval(1)
        while outcome == nil, Date() < deadline {
            await Task.yield()
        }

        XCTAssertEqual(outcome, .needsAuthentication)
        let saved = try draftStore.list().first
        XCTAssertEqual(saved?.caption, "guest caption")
        XCTAssertEqual(saved?.pendingAuthentication, true)
    }

    func testAuthenticatedSubmitMarksPendingPublication() async throws {
        let draftStore = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let (draft, data) = try makeDraft(imageStore: imageStore, caption: nil)
        try draftStore.save(draft)

        let model = ReviewSubmissionViewModel(
            draft: draft,
            imageData: data,
            draftStore: draftStore,
            imageStore: imageStore,
            isAuthenticated: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
        model.submitToCommunity()

        let deadline = Date().addingTimeInterval(1)
        while !model.showsPublicationPlaceholder, Date() < deadline {
            await Task.yield()
        }

        XCTAssertTrue(model.showsPublicationPlaceholder)
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

    private func makeJPEG(color: UIColor = .red) -> Data {
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 6, height: 6))
        let image = renderer.image { context in
            color.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 6, height: 6))
        }
        return image.jpegData(compressionQuality: 0.9)!
    }
}
