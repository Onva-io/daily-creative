import Foundation
@preconcurrency import DailySketchAPI

enum FeedMapping {
    static func mapItem(_ item: FeedItem) -> FeedItemModel? {
        let creativeType = item.creativeType.rawValue
        let imageURL = item.imageUrl.flatMap(URL.init(string:))
        let thumbnailURL = item.thumbnailUrl.flatMap(URL.init(string:))

        if creativeType == "sketch", imageURL == nil || thumbnailURL == nil {
            return nil
        }

        return FeedItemModel(
            id: item.id,
            creativeType: creativeType,
            imageURL: imageURL,
            thumbnailURL: thumbnailURL,
            userId: item.user.id,
            username: item.user.username,
            displayName: item.user.displayName,
            avatarURL: item.user.avatarUrl.flatMap(URL.init(string:)),
            promptWords: [item.prompt.word1, item.prompt.word2, item.prompt.word3],
            promptDate: item.prompt.promptDate,
            timerMode: item.timerMode.rawValue,
            timerSeconds: item.timerSeconds,
            captionPreview: item.captionPreview,
            bodyPreview: item.bodyPreview,
            wordCount: item.wordCount,
            likeCount: item.likeCount,
            reflectionCount: item.reflectionCount,
            viewerHasLiked: item.viewerHasLiked,
            isOwner: item.isOwner,
            publishedAt: item.publishedAt
        )
    }

    static func apiCreativeType(from productID: String = ProductConfig.current.creativeTypeID) -> CreativeType? {
        CreativeType(rawValue: productID)
    }
}
