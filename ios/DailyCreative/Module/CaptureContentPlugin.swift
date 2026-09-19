import Foundation
import SwiftUI

/// An image as it leaves the capture step.
struct CapturedImage: Sendable {
    enum Source: Sendable {
        case camera
        case library
    }

    /// Normalised JPEG that becomes the draft image: orientation fixed,
    /// metadata dropped. This is what gets uploaded.
    let jpegData: Data
    /// Bytes exactly as the picker delivered them, metadata intact, so a type
    /// can read EXIF before it is lost. `nil` for camera captures, which never
    /// carry a location.
    let originalData: Data?
    let source: Source
}

/// Type-specific hooks into the shared capture → review → publish pipeline.
///
/// Sketch adds nothing to the image; photo adds a location. The pipeline never
/// knows which: it asks the plugin for one `CaptureExtrasControlling` per
/// review session, shows that controller's optional editor under the caption,
/// stores whatever it encodes on the draft, and asks it for the publication
/// payload when the upload is done.
@MainActor
protocol CaptureContentPlugin: AnyObject {
    /// Copy under "Add your <noun>" on the capture source screen.
    var captureInstructions: String { get }

    /// `captured` is present only for a freshly taken or picked image. A
    /// reopened draft passes `nil` and the controller restores itself from
    /// `draft.contentExtras`.
    func makeExtrasController(
        draft: LocalDraft,
        captured: CapturedImage?
    ) -> any CaptureExtrasControlling
}

/// Owns the type-specific state of one draft while it is being reviewed.
@MainActor
protocol CaptureExtrasControlling: AnyObject {
    /// Opaque blob persisted as `LocalDraft.contentExtras` whenever the draft
    /// is saved. Only this type ever decodes it.
    func encodeExtras() throws -> Data?
    /// Editor rendered below the caption on the review screen, or `nil`.
    func makeReviewView(isDisabled: Bool) -> AnyView?
    /// The user swapped the image while reviewing.
    func handleImageReplaced(_ captured: CapturedImage)
    func makePublicationContent(uploadId: UUID, caption: String?) -> PublicationContent
}

extension CaptureExtrasControlling {
    func handleImageReplaced(_ captured: CapturedImage) {}
}

/// Daily Sketch: the upload and caption are the whole payload.
@MainActor
final class SketchCapturePlugin: CaptureContentPlugin {
    let captureInstructions = "Photograph your drawing or choose an existing photo from your library."

    func makeExtrasController(
        draft: LocalDraft,
        captured: CapturedImage?
    ) -> any CaptureExtrasControlling {
        SketchExtrasController()
    }
}

@MainActor
final class SketchExtrasController: CaptureExtrasControlling {
    func encodeExtras() throws -> Data? { nil }

    func makeReviewView(isDisabled: Bool) -> AnyView? { nil }

    func makePublicationContent(uploadId: UUID, caption: String?) -> PublicationContent {
        .sketch(uploadId: uploadId, caption: caption)
    }
}
