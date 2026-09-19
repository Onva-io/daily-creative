import SwiftUI

struct SubmissionCard: View {
    let item: FeedItemModel
    var onTapArtwork: () -> Void
    var onTapOwner: () -> Void
    var onTapLike: (() -> Void)?
    var onTapReflection: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            ownerRow
            artwork
            metadataRow
            if let caption = item.captionPreview, !caption.isEmpty {
                Text(caption)
                    .font(AppTypography.bodySmall)
                    .foregroundStyle(AppColors.textSecondary)
                    .lineLimit(3)
                    .accessibilityLabel("Caption preview: \(caption)")
            }
            socialRow
        }
        .accessibilityElement(children: .contain)
    }

    private var ownerRow: some View {
        Button(action: onTapOwner) {
            HStack(spacing: AppSpacing.xs) {
                AvatarView(
                    displayName: item.displayName,
                    username: item.username,
                    avatarURL: item.avatarURL,
                    size: .feed
                )
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.displayName)
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)
                        .lineLimit(1)
                    Text("@\(item.username)")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)
                        .lineLimit(1)
                }
                Spacer(minLength: AppSpacing.xs)
                Text(item.relativePublishedAt)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(item.displayName), @\(item.username)")
        .accessibilityHint("Opens profile")
    }

    private var artwork: some View {
        Button(action: onTapArtwork) {
            SubmissionContentView(content: item.content, context: .feed)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(artworkAccessibilityLabel)
        .accessibilityHint("Opens \(item.content.kindNoun) detail")
    }

    private var metadataRow: some View {
        Text(item.metadataLine)
            .font(AppTypography.caption)
            .foregroundStyle(AppColors.textTertiary)
            .accessibilityLabel(item.metadataLine)
    }

    private var socialRow: some View {
        HStack(spacing: AppSpacing.lg) {
            SocialActionButton(
                kind: .like,
                count: item.likeCount,
                isActive: item.viewerHasLiked,
                action: { onTapLike?() }
            )
            SocialActionButton(
                kind: .reflection,
                count: item.reflectionCount,
                action: { onTapReflection?() }
            )
            Spacer()
        }
    }

    private var artworkAccessibilityLabel: String {
        let kind = item.content.kindLabel
        if let preview = item.content.textPreview, !preview.isEmpty {
            return "\(kind) by \(item.displayName). \(preview)"
        }
        if let caption = item.captionPreview, !caption.isEmpty {
            return "\(kind) by \(item.displayName). \(caption)"
        }
        return "\(kind) by \(item.displayName). Prompt: \(item.promptWords.joined(separator: ", "))"
    }
}

#Preview("Light") {
    ScrollView {
        SubmissionCard(
            item: FeedItemModel.preview,
            onTapArtwork: {},
            onTapOwner: {}
        )
        .padding(.horizontal, AppSpacing.screenHorizontal)
    }
    .background(AppColors.background)
}

#Preview("Dark") {
    ScrollView {
        SubmissionCard(
            item: FeedItemModel.preview,
            onTapArtwork: {},
            onTapOwner: {}
        )
        .padding(.horizontal, AppSpacing.screenHorizontal)
    }
    .background(AppColors.background)
    .preferredColorScheme(.dark)
}
