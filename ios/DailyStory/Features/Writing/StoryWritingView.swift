import SwiftUI

struct StoryWritingView: View {
    @Binding var text: String
    let promptWords: [String]?
    let wordCount: Int
    let onPublish: () -> Void
    let onSaveDraft: () -> Void
    let isPublishing: Bool
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if let words = promptWords {
                    HStack(spacing: AppSpacing.sm) {
                        ForEach(words, id: \.self) { word in
                            PromptChip(word: word)
                        }
                    }
                    .padding(.horizontal, AppSpacing.screenHorizontal)
                    .padding(.vertical, AppSpacing.md)
                }

                TextEditor(text: $text)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textPrimary)
                    .scrollContentBackground(.hidden)
                    .padding(.horizontal, AppSpacing.screenHorizontal)
                    .frame(maxHeight: .infinity)

                Divider()

                HStack {
                    Text("\(wordCount) words")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)

                    Spacer()

                    PrimaryButton(
                        title: "Publish",
                        action: onPublish,
                        isDisabled: text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isPublishing
                    )
                }
                .padding(.horizontal, AppSpacing.screenHorizontal)
                .padding(.vertical, AppSpacing.md)
            }
            .background(AppColors.background)
            .navigationTitle("Write Your Story")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Save Draft") {
                        onSaveDraft()
                        dismiss()
                    }
                }
            }
        }
    }
}
