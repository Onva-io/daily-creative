import Foundation
import Observation
import UIKit

enum ReviewSubmissionOutcome: Equatable, Sendable {
    case savedToDrafts
    case continueLater
    case published(SubmissionModel)
    case needsAuthentication
    case needsProfileCompletion
}

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
    private(set) var isPublishing = false
    private(set) var uploadProgress: Double = 0
    private(set) var bannerMessage: String?
    private(set) var validationErrorMessage: String?
    private(set) var publishErrorMessage: String?

    var caption: String {
        didSet {
            if caption.count > ReviewSubmissionLimits.maxCaptionLength {
                caption = String(caption.prefix(ReviewSubmissionLimits.maxCaptionLength))
            }
        }
    }

    private let draftStore: any DraftStoring
    private let imageStore: any DraftImageStoring
    private let uploadService: (any UploadServing)?
    private let submissionService: (any SubmissionServing)?
    private let sessionService: (any SketchSessionServing)?
    private let directUploader: (any DirectUploadTransporting)?
    private let publishedStore: (any PublishedSubmissionStoring)?
    private let accessTokenProvider: () -> String?
    private let isAuthenticated: () -> Bool
    private let canPublish: () -> Bool
    private let dateProvider: any DateProviding
    private let onFinished: (ReviewSubmissionOutcome) -> Void
    private let onReplaceRequested: () -> Void
    private let onPublished: ((SubmissionModel) -> Void)?

    init(
        draft: LocalDraft,
        imageData: Data,
        draftStore: any DraftStoring,
        imageStore: any DraftImageStoring,
        uploadService: (any UploadServing)? = nil,
        submissionService: (any SubmissionServing)? = nil,
        sessionService: (any SketchSessionServing)? = nil,
        directUploader: (any DirectUploadTransporting)? = nil,
        publishedStore: (any PublishedSubmissionStoring)? = nil,
        accessTokenProvider: @escaping () -> String? = { nil },
        isAuthenticated: @escaping () -> Bool,
        canPublish: @escaping () -> Bool = { true },
        dateProvider: any DateProviding = SystemDateProvider(),
        onFinished: @escaping (ReviewSubmissionOutcome) -> Void,
        onReplaceRequested: @escaping () -> Void,
        onPublished: ((SubmissionModel) -> Void)? = nil
    ) {
        self.draft = draft
        self.imageData = imageData
        self.previewImage = UIImage(data: imageData)
        self.caption = draft.caption ?? ""
        self.draftStore = draftStore
        self.imageStore = imageStore
        self.uploadService = uploadService
        self.submissionService = submissionService
        self.sessionService = sessionService
        self.directUploader = directUploader
        self.publishedStore = publishedStore
        self.accessTokenProvider = accessTokenProvider
        self.isAuthenticated = isAuthenticated
        self.canPublish = canPublish
        self.dateProvider = dateProvider
        self.onFinished = onFinished
        self.onReplaceRequested = onReplaceRequested
        self.onPublished = onPublished
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

    var uploadProgressLabel: String {
        let percent = Int((uploadProgress * 100).rounded())
        return "Uploading \(percent)%"
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
        draft.uploadId = nil
        draft.updatedAt = dateProvider.now()
        try draftStore.save(draft)
        try? imageStore.delete(fileName: previousFileName)
        imageData = jpeg
        previewImage = UIImage(data: jpeg)
        validationErrorMessage = nil
        publishErrorMessage = nil
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
            await publish()
        }
    }

    func retryPublish() {
        Task {
            await publish()
        }
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

    private func publish() async {
        isPublishing = true
        uploadProgress = 0
        publishErrorMessage = nil
        defer { isPublishing = false }

        do {
            try persistCaption(
                pendingAuthentication: !isAuthenticated(),
                pendingPublication: true
            )

            guard isAuthenticated() else {
                onFinished(.needsAuthentication)
                return
            }
            guard canPublish() else {
                onFinished(.needsProfileCompletion)
                return
            }
            guard let token = accessTokenProvider(),
                  let uploadService,
                  let submissionService,
                  let directUploader else {
                throw PublicationAPIError.underlying("Publishing is not configured.")
            }

            var serverSessionId = draft.serverSessionId
            if serverSessionId == nil, let sessionService {
                let created = try await sessionService.createSession(
                    accessToken: token,
                    promptId: draft.promptId,
                    timerMode: draft.timerMode,
                    selectedTimerSeconds: draft.selectedTimerSeconds,
                    clientTimezone: TimeZone.current.identifier,
                    clientSessionId: draft.localSessionId.uuidString,
                    idempotencyKey: "draft-session-\(draft.id.uuidString)"
                )
                serverSessionId = created.id
                draft.serverSessionId = created.id
                try draftStore.save(draft)
                _ = try? await sessionService.postEvent(
                    accessToken: token,
                    sessionId: created.id,
                    eventType: "photo_step_reached",
                    clientOccurredAt: dateProvider.now()
                )
            }
            guard let sessionId = serverSessionId else {
                throw PublicationAPIError.sessionNotFound
            }

            if let sessionService {
                _ = try? await sessionService.postEvent(
                    accessToken: token,
                    sessionId: sessionId,
                    eventType: "upload_started",
                    clientOccurredAt: dateProvider.now()
                )
            }

            let slot = try await uploadService.createUpload(
                accessToken: token,
                contentType: "image/jpeg",
                byteSize: imageData.count,
                purpose: .submission,
                idempotencyKey: "upload-\(draft.id.uuidString)"
            )
            draft.uploadId = slot.id
            try draftStore.save(draft)

            guard let signedURL = slot.signedUploadURL,
                  let method = slot.signedUploadMethod else {
                throw PublicationAPIError.uploadNotReady
            }
            try await directUploader.upload(
                data: imageData,
                to: signedURL,
                method: method,
                headers: slot.signedUploadHeaders
            ) { [weak self] value in
                Task { @MainActor in
                    self?.uploadProgress = value
                }
            }

            _ = try await uploadService.completeUpload(accessToken: token, uploadId: slot.id)
            if let sessionService {
                _ = try? await sessionService.postEvent(
                    accessToken: token,
                    sessionId: sessionId,
                    eventType: "upload_completed",
                    clientOccurredAt: dateProvider.now()
                )
            }

            let idempotencyKey = draft.publicationIdempotencyKey ?? UUID().uuidString
            draft.publicationIdempotencyKey = idempotencyKey
            try draftStore.save(draft)

            let trimmed = caption.trimmingCharacters(in: .whitespacesAndNewlines)
            let submission = try await submissionService.createSubmission(
                accessToken: token,
                sketchSessionId: sessionId,
                uploadId: slot.id,
                caption: trimmed.isEmpty ? nil : trimmed,
                idempotencyKey: idempotencyKey
            )

            let published = PublishedLocalSubmission(
                id: submission.id,
                promptId: draft.promptId,
                promptDate: draft.promptDate,
                timerMode: draft.timerMode,
                selectedTimerSeconds: draft.selectedTimerSeconds,
                caption: submission.caption,
                publishedAt: submission.publishedAt
            )
            try? publishedStore?.save(published)
            onPublished?(submission)
            onFinished(.published(submission))
        } catch {
            publishErrorMessage = error.localizedDescription
            try? persistCaption(pendingAuthentication: false, pendingPublication: true)
        }
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
