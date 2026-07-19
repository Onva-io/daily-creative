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

                    if model.isPublishing {
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            ProgressView(value: model.uploadProgress)
                                .tint(AppColors.primary)
                                .accessibilityLabel(model.uploadProgressLabel)
                                .accessibilityValue("\(Int((model.uploadProgress * 100).rounded())) percent")
                            Text(model.uploadProgressLabel)
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }

                    if let validationErrorMessage = model.validationErrorMessage {
                        Text(validationErrorMessage)
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.danger)
                    }

                    if let publishErrorMessage = model.publishErrorMessage {
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text(publishErrorMessage)
                                .font(AppTypography.bodySmall)
                                .foregroundStyle(AppColors.danger)
                                .accessibilityLabel("Publish failed. \(publishErrorMessage)")
                            PrimaryButton(
                                title: "Retry Publish",
                                action: { model.retryPublish() },
                                isDisabled: model.isPublishing || model.isSaving
                            )
                            TertiaryTextButton(
                                title: "Save to Drafts",
                                action: { model.saveToDrafts() },
                                isDisabled: model.isPublishing || model.isSaving
                            )
                        }
                    }

                    if let bannerMessage = model.bannerMessage {
                        Text(bannerMessage)
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.success)
                    }

                    if model.publishErrorMessage == nil {
                        PrimaryButton(
                            title: model.isPublishing ? "Publishing…" : "Submit to Community",
                            action: { model.submitToCommunity() },
                            isDisabled: model.isSaving || model.isPublishing
                        )
                        .accessibilityHint("Uploads your sketch and publishes it to the community")

                        TertiaryTextButton(
                            title: "Save to Drafts",
                            action: { model.saveToDrafts() },
                            isDisabled: model.isSaving || model.isPublishing
                        )
                    }
                }
                .padding(.horizontal, AppSpacing.screenHorizontal)
                .padding(.vertical, AppSpacing.lg)
            }
            .scrollDismissesKeyboard(.interactively)
            .background(AppColors.background.ignoresSafeArea())
            .navigationTitle("Review")
            .navigationBarTitleDisplayMode(.inline)
            .disabled(model.isPublishing)
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
            .disabled(model.isPublishing)
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
            .disabled(model.isPublishing)

            if let characterCountLabel = model.characterCountLabel {
                Text(characterCountLabel)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }
}

#Preview("Normal") {
    ReviewSubmissionView(
        model: ReviewSubmissionViewModel(
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
            imageData: Data(),
            draftStore: InMemoryDraftStore(),
            imageStore: InMemoryDraftImageStore(),
            isAuthenticated: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
    )
}

#Preview("Dark") {
    ReviewSubmissionView(
        model: ReviewSubmissionViewModel(
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
                caption: "A quiet still life.",
                createdAt: Date(),
                updatedAt: Date(),
                pendingAuthentication: false,
                pendingPublication: false
            ),
            imageData: Data(),
            draftStore: InMemoryDraftStore(),
            imageStore: InMemoryDraftImageStore(),
            isAuthenticated: { true },
            onFinished: { _ in },
            onReplaceRequested: {}
        )
    )
    .preferredColorScheme(.dark)
}
