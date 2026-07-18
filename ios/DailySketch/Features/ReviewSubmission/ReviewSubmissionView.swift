import SwiftUI

struct ReviewSubmissionView: View {
    @Bindable var model: ReviewSubmissionViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
                    Text("Ready to share?")
                        .font(AppTypography.title2)
                        .foregroundStyle(AppColors.textPrimary)

                    Text("Review your sketch before sharing it with the community.")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)

                    imagePreview

                    metadataRow

                    Text(model.timerLabel)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)

                    captionSection

                    if let validationErrorMessage = model.validationErrorMessage {
                        Text(validationErrorMessage)
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.danger)
                    }

                    if let bannerMessage = model.bannerMessage {
                        Text(bannerMessage)
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.success)
                    }

                    PrimaryButton(
                        title: "Submit to Community",
                        action: { model.submitToCommunity() },
                        isDisabled: model.isSaving
                    )

                    TertiaryTextButton(
                        title: "Save to Drafts",
                        action: { model.saveToDrafts() },
                        isDisabled: model.isSaving
                    )
                }
                .padding(.horizontal, AppSpacing.screenHorizontal)
                .padding(.vertical, AppSpacing.lg)
            }
            .scrollDismissesKeyboard(.interactively)
            .background(AppColors.background.ignoresSafeArea())
            .navigationTitle("Review")
            .navigationBarTitleDisplayMode(.inline)
            .alert(
                "Publishing arrives next",
                isPresented: Binding(
                    get: { model.showsPublicationPlaceholder },
                    set: { if !$0 { model.acknowledgePublicationPlaceholder() } }
                )
            ) {
                Button("OK") {
                    model.acknowledgePublicationPlaceholder()
                }
            } message: {
                Text("Your sketch is saved as a Draft. Community upload arrives in the next update.")
            }
        }
    }

    private var imagePreview: some View {
        ZStack(alignment: .bottomTrailing) {
            Group {
                if let previewImage = model.previewImage {
                    Image(uiImage: previewImage)
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: .infinity)
                        .clipShape(RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous))
                } else {
                    RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous)
                        .fill(AppColors.surfaceTertiary)
                        .frame(height: 280)
                        .overlay {
                            Image(systemName: "photo")
                                .foregroundStyle(AppColors.textTertiary)
                        }
                }
            }
            .appSoftShadow()

            Button {
                model.replaceImageRequested()
            } label: {
                Label("Replace", systemImage: "arrow.triangle.2.circlepath.camera")
                    .font(AppTypography.caption.weight(.semibold))
                    .foregroundStyle(AppColors.textPrimary)
                    .padding(.horizontal, AppSpacing.md)
                    .padding(.vertical, AppSpacing.sm)
                    .background(AppColors.surfacePrimary.opacity(0.92))
                    .clipShape(Capsule())
            }
            .padding(AppSpacing.md)
            .accessibilityLabel("Replace or retake photo")
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Sketch preview")
    }

    private var metadataRow: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text(model.promptDateLabel)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textTertiary)

            PromptGroup(
                words: model.draft.promptWords,
                accessibilityLabel: model.draft.promptAccessibilityLabel
            )
        }
    }

    private var captionSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("Optional caption")
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)

            TextField(
                "Add a thought about your creative process…",
                text: $model.caption,
                axis: .vertical
            )
            .lineLimit(3...6)
            .padding(AppSpacing.md)
            .background(AppColors.surfaceTertiary)
            .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
            .accessibilityLabel("Optional caption")

            if let characterCountLabel = model.characterCountLabel {
                Text(characterCountLabel)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }
}
