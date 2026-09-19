import Foundation
@preconcurrency import DailyCreativeAPI

enum FeedMapping {
    static func mapItem(_ item: FeedItem) -> FeedItemModel? {
        let content = mapContent(item.content)
        guard content.isRenderable else { return nil }

        return FeedItemModel(
            id: item.id,
            creativeType: item.creativeType.rawValue,
            content: content,
            userId: item.user.id,
            username: item.user.username,
            displayName: item.user.displayName,
            avatarURL: item.user.avatarUrl.flatMap(URL.init(string:)),
            promptWords: [item.prompt.word1, item.prompt.word2, item.prompt.word3],
            promptDate: item.prompt.promptDate,
            timerMode: item.timerMode.rawValue,
            timerSeconds: item.timerSeconds,
            captionPreview: item.captionPreview,
            likeCount: item.likeCount,
            reflectionCount: item.reflectionCount,
            viewerHasLiked: item.viewerHasLiked,
            isOwner: item.isOwner,
            publishedAt: item.publishedAt
        )
    }

    /// The single place the API's discriminated `content` union becomes an
    /// app model. Adding a creative type means adding one case here.
    static func mapContent(_ content: SubmissionContent) -> SubmissionContentModel {
        switch content {
        case .typeSketchContent(let sketch):
            return .sketch(
                SketchContentModel(
                    imageURL: sketch.imageUrl.flatMap(URL.init(string:)),
                    thumbnailURL: sketch.thumbnailUrl.flatMap(URL.init(string:))
                )
            )
        case .typeStoryContent(let story):
            return .story(
                StoryContentModel(
                    body: story.body,
                    bodyPreview: story.bodyPreview,
                    wordCount: story.wordCount
                )
            )
        case .typePhotoContent(let photo):
            return .photo(
                PhotoContentModel(
                    imageURL: photo.imageUrl.flatMap(URL.init(string:)),
                    thumbnailURL: photo.thumbnailUrl.flatMap(URL.init(string:)),
                    location: photo.location.map { location in
                        PhotoLocationModel(
                            label: location.label,
                            latitude: location.latitude,
                            longitude: location.longitude,
                            exactShared: location.exactShared
                        )
                    }
                )
            )
        }
    }

    static func apiCreativeType(from productID: String = ProductConfig.current.creativeTypeID) -> CreativeType {
        CreativeType(rawValue: productID) ?? .sketch
    }
}
