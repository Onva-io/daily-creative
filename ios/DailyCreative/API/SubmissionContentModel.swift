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

/// A photo's place as the API projected it for the requesting user.
///
/// `latitude`/`longitude` are present only when the author opted in to exact
/// sharing or the viewer is the author; everyone else gets the author's own
/// `label`. The client never derives one from the other.
struct PhotoLocationModel: Codable, Equatable, Sendable {
    let label: String?
    let latitude: Double?
    let longitude: Double?
    let exactShared: Bool

    var hasCoordinates: Bool {
        latitude != nil && longitude != nil
    }

    /// Anything worth rendering at all.
    var isPresentable: Bool {
        (label?.isEmpty == false) || hasCoordinates
    }
}

/// Photo-specific published content: the image plus an optional place.
struct PhotoContentModel: Codable, Equatable, Sendable {
    let imageURL: URL?
    let thumbnailURL: URL?
    let location: PhotoLocationModel?
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
    case photo(PhotoContentModel)
    /// A creative type this build does not know how to render. Kept so caches
    /// and mixed feeds decode instead of failing wholesale.
    case unsupported(creativeType: String)

    /// "Sketch" / "Story" / "Photo" — for accessibility labels and titles.
    var kindLabel: String {
        switch self {
        case .sketch: return "Sketch"
        case .story: return "Story"
        case .photo: return "Photo"
        case .unsupported: return "Submission"
        }
    }

    /// "sketch" / "story" / "photo" — for sentences.
    var kindNoun: String {
        kindLabel.lowercased()
    }

    /// Display image, when the type has one.
    var imageURL: URL? {
        switch self {
        case .sketch(let sketch): return sketch.imageURL
        case .photo(let photo): return photo.imageURL
        case .story, .unsupported: return nil
        }
    }

    var thumbnailURL: URL? {
        switch self {
        case .sketch(let sketch): return sketch.thumbnailURL
        case .photo(let photo): return photo.thumbnailURL
        case .story, .unsupported: return nil
        }
    }

    /// Full text body (detail only), when the type has one.
    var body: String? {
        switch self {
        case .story(let story): return story.body
        case .sketch, .photo, .unsupported: return nil
        }
    }

    /// Short text preview for list surfaces, when the type has one.
    var textPreview: String? {
        switch self {
        case .story(let story): return story.bodyPreview
        case .sketch, .photo, .unsupported: return nil
        }
    }

    var wordCount: Int? {
        switch self {
        case .story(let story): return story.wordCount
        case .sketch, .photo, .unsupported: return nil
        }
    }

    /// Where the work was made, when the type records one and the API chose
    /// to reveal it to this viewer.
    var location: PhotoLocationModel? {
        switch self {
        case .photo(let photo): return photo.location
        case .sketch, .story, .unsupported: return nil
        }
    }

    /// False when the item cannot be shown at all (e.g. a sketch whose signed
    /// URLs are missing). Such items are dropped from lists.
    var isRenderable: Bool {
        switch self {
        case .sketch(let sketch):
            return sketch.imageURL != nil && sketch.thumbnailURL != nil
        case .photo(let photo):
            return photo.imageURL != nil && photo.thumbnailURL != nil
        case .story:
            return true
        case .unsupported:
            return false
        }
    }
}
