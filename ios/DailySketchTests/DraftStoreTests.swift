import UIKit
import XCTest
@testable import DailySketch

@MainActor
final class DraftStoreTests: XCTestCase {
    func testImageSurvivesReloadFromDisk() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("DraftStoreTests-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let metadataURL = directory.appendingPathComponent("drafts.json")
        let imagesDir = directory.appendingPathComponent("images", isDirectory: true)
        try FileManager.default.createDirectory(at: imagesDir, withIntermediateDirectories: true)

        let imageStore = DraftImageStore(directory: imagesDir)
        let store = DraftStore(fileURL: metadataURL)

        let jpeg = makeJPEG()
        let fileName = try imageStore.write(jpeg)
        let draft = LocalDraft(
            id: UUID(),
            localSessionId: UUID(),
            serverSessionId: nil,
            promptId: UUID(),
            promptWords: ["Chocolate", "Coffee", "Banana"],
            promptAccessibilityLabel: "Today’s prompt: Chocolate, Coffee, Banana.",
            promptDate: Date(timeIntervalSince1970: 1_784_332_800),
            timerMode: "countdown",
            selectedTimerSeconds: 180,
            sessionStartedAt: Date(timeIntervalSince1970: 1_784_332_800),
            imageFileName: fileName,
            caption: "first pass",
            createdAt: Date(timeIntervalSince1970: 1_784_332_810),
            updatedAt: Date(timeIntervalSince1970: 1_784_332_820),
            pendingAuthentication: true,
            pendingPublication: false
        )
        try store.save(draft)

        let reloadedStore = DraftStore(fileURL: metadataURL)
        let reloadedImages = DraftImageStore(directory: imagesDir)
        let loaded = try reloadedStore.mostRecentRecoverable()
        XCTAssertEqual(loaded?.id, draft.id)
        XCTAssertEqual(loaded?.caption, "first pass")
        let data = try reloadedImages.readData(fileName: fileName)
        XCTAssertFalse(data.isEmpty)
        XCTAssertNotNil(UIImage(data: data))
    }

    func testPurgeExpiredRemovesOldDrafts() throws {
        let store = InMemoryDraftStore()
        let imageStore = InMemoryDraftImageStore()
        let oldName = try imageStore.write(makeJPEG())
        let freshName = try imageStore.write(makeJPEG())
        let now = Date(timeIntervalSince1970: 2_000_000_000)

        try store.save(
            LocalDraft(
                id: UUID(),
                localSessionId: UUID(),
                serverSessionId: nil,
                promptId: UUID(),
                promptWords: ["A", "B", "C"],
                promptAccessibilityLabel: "prompt",
                promptDate: now.addingTimeInterval(-40 * 24 * 60 * 60),
                timerMode: "no_timer",
                selectedTimerSeconds: nil,
                sessionStartedAt: now.addingTimeInterval(-40 * 24 * 60 * 60),
                imageFileName: oldName,
                caption: nil,
                createdAt: now.addingTimeInterval(-40 * 24 * 60 * 60),
                updatedAt: now.addingTimeInterval(-40 * 24 * 60 * 60),
                pendingAuthentication: false,
                pendingPublication: false
            )
        )
        try store.save(
            LocalDraft(
                id: UUID(),
                localSessionId: UUID(),
                serverSessionId: nil,
                promptId: UUID(),
                promptWords: ["D", "E", "F"],
                promptAccessibilityLabel: "prompt",
                promptDate: now,
                timerMode: "countdown",
                selectedTimerSeconds: 60,
                sessionStartedAt: now,
                imageFileName: freshName,
                caption: nil,
                createdAt: now,
                updatedAt: now,
                pendingAuthentication: false,
                pendingPublication: false
            )
        )

        let expired = try store.purgeExpired(retentionDays: 30, now: now)
        XCTAssertEqual(expired.count, 1)
        XCTAssertEqual(try store.list().count, 1)
        for draft in expired {
            try imageStore.delete(fileName: draft.imageFileName)
        }
        XCTAssertFalse(imageStore.contains(oldName))
        XCTAssertTrue(imageStore.contains(freshName))
    }

    private func makeJPEG() -> Data {
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 4, height: 4))
        let image = renderer.image { context in
            UIColor.blue.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 4, height: 4))
        }
        return image.jpegData(compressionQuality: 0.9)!
    }
}
