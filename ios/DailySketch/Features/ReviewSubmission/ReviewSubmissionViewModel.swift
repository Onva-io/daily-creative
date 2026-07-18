import Foundation
import Observation
import UIKit

enum ReviewSubmissionOutcome: Equatable, Sendable {
    case savedToDrafts
    case continueLater
    case awaitingPublication
    case needsAuthentication
}

/// Provisional client caption limit until Phase 7 submissions OpenAPI defines the server max.
enum ReviewSubmissionLimits {
    static let maxCaptionLength = 280
}

@MainActor
@Observable
final class ReviewSubmissionViewModel {
    private(set) var draft: LocalDraft
    private(set) var imageData: Data
    private(set) var previewImage: UIImage?
    private(set) var isSaving = false
    private(set) var bannerMessage: String?
    private(set) var showsPublicationPlaceholder = false
    private(set) var validationErrorMessage: String?

    var caption: String {
        didSet {
            if caption.count > ReviewSubmissionLimits.maxCaptionLength {
                caption = String(caption.prefix(ReviewSubmissionLimits.maxCaptionLength))
            }
        }
    }

    private let draftStore: any DraftStoring
    private let imageStore: any DraftImageStoring
    private let isAuthenticated: () -> Bool
    private let dateProvider: any DateProviding
    private let onFinished: (ReviewSubmissionOutcome) -> Void
    private let onReplaceRequested: () -> Void

    init(
        draft: LocalDraft,
        imageData: Data,
        draftStore: any DraftStoring,
        imageStore: any DraftImageStoring,
        isAuthenticated: @escaping () -> Bool,
        dateProvider: any DateProviding = SystemDateProvider(),
        onFinished: @escaping (ReviewSubmissionOutcome) -> Void,
        onReplaceRequested: @escaping () -> Void
    ) {
        self.draft = draft
        self.imageData = imageData
        self.previewImage = UIImage(data: imageData)
        self.caption = draft.caption ?? ""
        self.draftStore = draftStore
        self.imageStore = imageStore
        self.isAuthenticated = isAuthenticated
        self.dateProvider = dateProvider
        self.onFinished = onFinished
        self.onReplaceRequested = onReplaceRequested
    }

    var characterCountLabel: String? {
        let length = caption.count
        guard length >= ReviewSubmissionLimits.maxCaptionLength - 40 else { return nil }
        return "\(length)/\(ReviewSubmissionLimits.maxCaptionLength)"
    }

    var timerLabel: String {
        draft.timerDisplayLabel
    }

    var promptDateLabel: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: draft.promptDate)
    }

    func replaceImageRequested() {
        onReplaceRequested()
    }

    func replaceImage(with data: Data) throws {
        let image = try ImageValidation.validatedImage(from: data)
        let jpeg = try ImageValidation.normalizedJPEGData(from: image)
        let previousFileName = draft.imageFileName
        let newFileName = try imageStore.write(jpeg)
        let trimmed = caption.trimmingCharacters(in: .whitespacesAndNewlines)
        draft.caption = trimmed.isEmpty ? nil : trimmed
        draft.imageFileName = newFileName
        draft.updatedAt = dateProvider.now()
        // Caption is intentionally preserved across replacement.
        try draftStore.save(draft)
        try? imageStore.delete(fileName: previousFileName)
        imageData = jpeg
        previewImage = UIImage(data: jpeg)
        validationErrorMessage = nil
        bannerMessage = nil
    }

    func saveToDrafts() {
        Task {
            isSaving = true
            defer { isSaving = false }
            do {
                try persistCaption(pendingAuthentication: draft.pendingAuthentication, pendingPublication: false)
                bannerMessage = "Saved to Drafts."
                onFinished(.savedToDrafts)
            } catch {
                validationErrorMessage = error.localizedDescription
            }
        }
    }

    func submitToCommunity() {
        Task {
            isSaving = true
            defer { isSaving = false }
            do {
                if isAuthenticated() {
                    try persistCaption(pendingAuthentication: false, pendingPublication: true)
                    showsPublicationPlaceholder = true
                } else {
                    try persistCaption(pendingAuthentication: true, pendingPublication: false)
                    onFinished(.needsAuthentication)
                }
            } catch {
                validationErrorMessage = error.localizedDescription
            }
        }
    }

    func acknowledgePublicationPlaceholder() {
        showsPublicationPlaceholder = false
        onFinished(.awaitingPublication)
    }

    func continueLaterFromAuthCheckpoint() throws {
        try persistCaption(pendingAuthentication: true, pendingPublication: false)
        onFinished(.continueLater)
    }

    /// Call after successful guest authentication to clear the pending-auth flag.
    func markAuthenticated() {
        draft.pendingAuthentication = false
        draft.updatedAt = dateProvider.now()
        try? draftStore.save(draft)
    }

    private func persistCaption(pendingAuthentication: Bool, pendingPublication: Bool) throws {
        let trimmed = caption.trimmingCharacters(in: .whitespacesAndNewlines)
        draft.caption = trimmed.isEmpty ? nil : trimmed
        draft.pendingAuthentication = pendingAuthentication
        draft.pendingPublication = pendingPublication
        draft.updatedAt = dateProvider.now()
        try draftStore.save(draft)
    }
}
