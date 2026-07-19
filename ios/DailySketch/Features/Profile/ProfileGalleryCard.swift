import SwiftUI

struct ProfileGalleryCard: View {
    let item: FeedItemModel
    var onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                artwork
                Text(promptLabel)
                    .font(AppTypography.headline)
                    .foregroundStyle(AppColors.textPrimary)
                    .lineLimit(2)
                Text(promptDateLabel)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
                if let caption = item.captionPreview, !caption.isEmpty {
                    Text(caption)
                        .font(AppTypography.bodySmall)
                        .foregroundStyle(AppColors.textSecondary)
                        .lineLimit(2)
                }
                HStack(spacing: AppSpacing.md) {
                    Label("\(item.likeCount)", systemImage: "heart")
                    Label("\(item.reflectionCount)", systemImage: "bubble.left")
                }
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textTertiary)
            }
            .padding(AppSpacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(AppColors.surfaceSecondary)
            .clipShape(RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Sketch for \(promptLabel), \(promptDateLabel)")
        .accessibilityHint("Opens submission detail")
    }

    private var artwork: some View {
        AsyncImage(url: item.imageURL) { phase in
            switch phase {
            case .empty:
                LoadingSkeleton(height: 240)
            case .success(let image):
                image
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity)
                    .frame(maxHeight: 420)
                    .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
            case .failure:
                RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous)
                    .fill(AppColors.surfaceTertiary)
                    .frame(height: 200)
                    .overlay {
                        Text("Couldn’t load image")
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.textTertiary)
                    }
            @unknown default:
                EmptyView()
            }
        }
    }

    private var promptLabel: String {
        item.promptWords.joined(separator: " · ")
    }

    private var promptDateLabel: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: item.promptDate)
    }
}
