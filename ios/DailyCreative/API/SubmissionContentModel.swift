import Foundation

/// Sketch-specific published content (signed image URLs).
struct SketchContentModel: Codable, Equatable, Sendable {
    let imageURL: URL?
    let thumbnailURL: URL?
}

/// Story-specific published content. `body` is only present on the detail
/// endpoint; list surfaces carry `bodyPreview`.
struct StoryContentModel: Codable, Equatable, Sendable {
    let body: String?
    let bodyPreview: String?
    let wordCount: Int
}

/// Type-specific part of a published Submission, mirroring the API's
/// discriminated `content` object. Shared fields (caption, timer, author,
/// prompt, counts) stay flat on `FeedItemModel` / `SubmissionModel`.
///
/// Every shared surface renders by switching on this value, so an app never
/// needs to know which creative type produced an item.
enum SubmissionContentModel: Codable, Equatable, Sendable {
    case sketch(SketchContentModel)
    case story(StoryContentModel)
    /// A creative type this build does not know how to render. Kept so caches
    /// and mixed feeds decode instead of failing wholesale.
    case unsupported(creativeType: String)

    /// "Sketch" / "Story" — for accessibility labels and titles.
    var kindLabel: String {
        switch self {
        case .sketch: return "Sketch"
        case .story: return "Story"
        case .unsupported: return "Submission"
        }
    }

    /// "sketch" / "story" — for sentences.
    var kindNoun: String {
        kindLabel.lowercased()
    }

    /// Display image, when the type has one.
    var imageURL: URL? {
        switch self {
        case .sketch(let sketch): return sketch.imageURL
        case .story, .unsupported: return nil
        }
    }

    var thumbnailURL: URL? {
        switch self {
        case .sketch(let sketch): return sketch.thumbnailURL
        case .story, .unsupported: return nil
        }
    }

    /// Full text body (detail only), when the type has one.
    var body: String? {
        switch self {
        case .story(let story): return story.body
        case .sketch, .unsupported: return nil
        }
    }

    /// Short text preview for list surfaces, when the type has one.
    var textPreview: String? {
        switch self {
        case .story(let story): return story.bodyPreview
        case .sketch, .unsupported: return nil
        }
    }

    var wordCount: Int? {
        switch self {
        case .story(let story): return story.wordCount
        case .sketch, .unsupported: return nil
        }
    }

    /// False when the item cannot be shown at all (e.g. a sketch whose signed
    /// URLs are missing). Such items are dropped from lists.
    var isRenderable: Bool {
        switch self {
        case .sketch(let sketch):
            return sketch.imageURL != nil && sketch.thumbnailURL != nil
        case .story:
            return true
        case .unsupported:
            return false
        }
    }
}
