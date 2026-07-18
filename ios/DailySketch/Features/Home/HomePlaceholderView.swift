import SwiftUI

struct HomePlaceholderView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
                Text("Today’s Inspiration")
                    .font(AppTypography.display)
                    .foregroundStyle(AppColors.textPrimary)

                Text("Use all three words as inspiration for today’s sketch.")
                    .font(AppTypography.bodyLarge)
                    .foregroundStyle(AppColors.textSecondary)

                VStack(alignment: .leading, spacing: AppSpacing.contentGap) {
                    promptCard("Prompt")
                    HStack(spacing: AppSpacing.contentGap) {
                        promptCard("words")
                        promptCard("soon")
                    }
                }

                PrimaryButton(title: "Start Sketch") {}
                    .disabled(true)

                Text("Community Sketches")
                    .font(AppTypography.title3)
                    .foregroundStyle(AppColors.textPrimary)

                Text("No sketches yet. Be the first to share an interpretation of today’s prompt.")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .padding(AppSpacing.cardPadding)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(AppColors.surfaceSecondary)
                    .clipShape(RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous))
            }
            .padding(.horizontal, AppSpacing.screenHorizontal)
            .padding(.vertical, AppSpacing.lg)
        }
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle("Daily Sketch")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func promptCard(_ word: String) -> some View {
        Text(word)
            .font(AppTypography.title3)
            .foregroundStyle(AppColors.textPrimary)
            .frame(maxWidth: .infinity, minHeight: 72, alignment: .leading)
            .padding(AppSpacing.cardPadding)
            .background(AppColors.surfacePrimary)
            .clipShape(RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous))
            .accessibilityHidden(true)
    }
}

#Preview {
    NavigationStack {
        HomePlaceholderView()
    }
}
