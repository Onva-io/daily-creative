import SwiftUI

/// Renders the type-specific part of a published item by switching on its
/// `SubmissionContentModel`. This is the single place shared surfaces learn
/// how each creative type looks; adding a type means adding one case here.
struct SubmissionContentView: View {
    enum Context {
        /// Feed card.
        case feed
        /// Profile gallery card.
        case gallery
        /// Submission detail screen (full body, larger image).
        case detail
    }

    let content: SubmissionContentModel
    let context: Context
    var accessibilityLabel: String? = nil

    var body: some View {
        switch content {
        case .sketch(let sketch):
            imageContent(url: sketch.imageURL)
        case .story(let story):
            textContent(
                text: context == .detail ? (story.body ?? story.bodyPreview) : story.bodyPreview,
                wordCount: story.wordCount
            )
        case .unsupported:
            unsupportedContent
        }
    }

    private var cornerRadius: CGFloat {
        context == .gallery ? AppRadii.medium : AppRadii.card
    }

    private func imageContent(url: URL?) -> some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .empty:
                LoadingSkeleton(height: skeletonHeight)
                    .accessibilityLabel("Loading artwork")
            case .success(let image):
                image
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity)
                    .frame(maxHeight: maxImageHeight)
            case .failure:
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(AppColors.surfaceTertiary)
                    .frame(height: failureHeight)
                    .overlay {
                        Text("Couldn’t load image")
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.textTertiary)
                    }
            @unknown default:
                EmptyView()
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        .accessibilityLabel(accessibilityLabel ?? "")
    }

    private func textContent(text: String?, wordCount: Int) -> some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text(text ?? "Untitled story")
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textPrimary)
                .lineLimit(context == .detail ? nil : (context == .feed ? 6 : 5))
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)

            if context != .detail {
                Text(wordCount == 1 ? "1 word" : "\(wordCount) words")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
            }
        }
        .padding(AppSpacing.md)
        .frame(maxWidth: .infinity, minHeight: context == .gallery ? 160 : nil, alignment: .leading)
        .background(context == .gallery ? AppColors.surfaceTertiary : AppColors.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        .accessibilityLabel(accessibilityLabel ?? (context == .detail ? "Story body" : ""))
    }

    private var unsupportedContent: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(AppColors.surfaceTertiary)
            .frame(height: failureHeight)
            .overlay {
                Text("Update the app to view this post")
                    .font(AppTypography.bodySmall)
                    .foregroundStyle(AppColors.textTertiary)
            }
    }

    private var skeletonHeight: CGFloat {
        switch context {
        case .feed: 280
        case .gallery: 240
        case .detail: 320
        }
    }

    private var maxImageHeight: CGFloat? {
        switch context {
        case .feed: 480
        case .gallery: 420
        case .detail: nil
        }
    }

    private var failureHeight: CGFloat {
        switch context {
        case .feed: 220
        case .gallery: 200
        case .detail: 280
        }
    }
}
