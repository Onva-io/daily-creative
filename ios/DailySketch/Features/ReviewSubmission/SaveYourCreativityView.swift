import SwiftUI

struct SaveYourCreativityView: View {
    let thumbnail: UIImage?
    let onCreateAccount: () -> Void
    let onSignIn: () -> Void
    let onContinueLater: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppSpacing.contentGapLarge) {
                    Spacer(minLength: AppSpacing.section)

                    thumbnailView
                        .frame(width: 160, height: 160)
                        .clipShape(RoundedRectangle(cornerRadius: AppRadii.hero, style: .continuous))
                        .appSoftShadow()
                        .accessibilityLabel("Your sketch preview")

                    Text("Save Your Creativity")
                        .font(AppTypography.title2)
                        .foregroundStyle(AppColors.textPrimary)
                        .multilineTextAlignment(.center)

                    Text("Create a free account to save your sketches, build your history, and share with the community.")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                        .multilineTextAlignment(.center)

                    VStack(spacing: AppSpacing.contentGap) {
                        PrimaryButton(
                            title: "Create Free Account",
                            action: onCreateAccount
                        )
                        SecondaryButton(
                            title: "Sign In",
                            action: onSignIn
                        )
                        TertiaryTextButton(
                            title: "Continue Later",
                            action: onContinueLater
                        )
                    }
                    .padding(.top, AppSpacing.md)

                    Spacer(minLength: AppSpacing.section)
                }
                .padding(.horizontal, AppSpacing.screenHorizontal)
                .padding(.vertical, AppSpacing.lg)
            }
            .background(AppColors.background.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
        }
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
}

#Preview {
    SaveYourCreativityView(
        thumbnail: nil,
        onCreateAccount: {},
        onSignIn: {},
        onContinueLater: {}
    )
}
