import SwiftUI

struct DraftCardView: View {
    let draft: LocalDraft
    let thumbnail: UIImage?
    let onContinue: () -> Void
    let onDiscard: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("Ready when you are")
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)

            HStack(alignment: .center, spacing: AppSpacing.md) {
                thumbnailView
                    .frame(width: 64, height: 64)
                    .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 4) {
                    Text(promptDateLabel)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)
                    Text(draft.promptWords.joined(separator: " · "))
                        .font(AppTypography.bodySmall)
                        .foregroundStyle(AppColors.textSecondary)
                        .lineLimit(2)
                }

                Spacer(minLength: 0)
            }

            HStack(spacing: AppSpacing.contentGap) {
                PrimaryButton(title: "Continue", action: onContinue)
                SecondaryButton(title: "Discard", action: onDiscard)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.large, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Draft ready when you are")
    }

    @ViewBuilder
    private var thumbnailView: some View {
        if let thumbnail {
            Image(uiImage: thumbnail)
                .resizable()
                .scaledToFill()
        } else {
            AppColors.surfaceTertiary
                .overlay {
                    Image(systemName: "photo")
                        .foregroundStyle(AppColors.textTertiary)
                }
        }
    }

    private var promptDateLabel: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: draft.promptDate)
    }
}

#Preview {
    DraftCardView(
        draft: LocalDraft(
            id: UUID(),
            localSessionId: UUID(),
            serverSessionId: nil,
            promptId: UUID(),
            promptWords: ["Chocolate", "Coffee", "Banana"],
            promptAccessibilityLabel: "Today’s prompt: Chocolate, Coffee, Banana.",
            promptDate: Date(),
            timerMode: "countdown",
            selectedTimerSeconds: 300,
            sessionStartedAt: Date(),
            imageFileName: "preview.jpg",
            caption: nil,
            createdAt: Date(),
            updatedAt: Date(),
            pendingAuthentication: false,
            pendingPublication: false
        ),
        thumbnail: nil,
        onContinue: {},
        onDiscard: {}
    )
    .padding()
    .background(AppColors.background)
}
