import SwiftUI

struct SubmissionDetailView: View {
    @State private var model: SubmissionDetailViewModel

    init(model: SubmissionDetailViewModel) {
        _model = State(initialValue: model)
    }

    var body: some View {
        Group {
            switch model.state {
            case .loading:
                LoadingView(message: "Loading your sketch…")
                    .accessibilityLabel("Loading submission")

            case .failed(let message):
                ErrorStateView(
                    title: "Couldn’t load this sketch",
                    message: message,
                    onRetry: { Task { await model.load() } }
                )

            case .loaded(let submission):
                ScrollView {
                    VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
                        AsyncImage(url: submission.imageURL) { phase in
                            switch phase {
                            case .empty:
                                LoadingSkeleton(height: 320)
                                    .accessibilityLabel("Loading artwork")
                            case .success(let image):
                                image
                                    .resizable()
                                    .scaledToFit()
                                    .frame(maxWidth: .infinity)
                                    .clipShape(
                                        RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous)
                                    )
                                    .accessibilityLabel("Your published sketch")
                            case .failure:
                                RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous)
                                    .fill(AppColors.surfaceTertiary)
                                    .frame(height: 280)
                                    .overlay {
                                        Text("Couldn’t load image")
                                            .font(AppTypography.bodySmall)
                                            .foregroundStyle(AppColors.textTertiary)
                                    }
                            @unknown default:
                                EmptyView()
                            }
                        }

                        PromptGroup(
                            words: submission.promptWords,
                            accessibilityLabel: "Prompt: \(submission.promptWords.joined(separator: ", "))"
                        )

                        HStack(spacing: AppSpacing.md) {
                            Text(model.promptDateLabel)
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textTertiary)
                            Text(model.timerLabel)
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textTertiary)
                        }
                        .accessibilityElement(children: .combine)

                        if let caption = submission.caption, !caption.isEmpty {
                            Text(caption)
                                .font(AppTypography.body)
                                .foregroundStyle(AppColors.textPrimary)
                                .accessibilityLabel("Caption: \(caption)")
                        }
                    }
                    .padding(.horizontal, AppSpacing.screenHorizontal)
                    .padding(.vertical, AppSpacing.lg)
                }
            }
        }
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle("Your Sketch")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await model.load()
        }
    }
}

#Preview("Loading") {
    NavigationStack {
        SubmissionDetailView(
            model: SubmissionDetailViewModel(
                submissionId: UUID(),
                submissionService: RecordingSubmissionRepository(),
                accessTokenProvider: { nil }
            )
        )
    }
}

#Preview("Dark") {
    NavigationStack {
        SubmissionDetailView(
            model: SubmissionDetailViewModel(
                submissionId: UUID(),
                submissionService: {
                    let repo = RecordingSubmissionRepository()
                    repo.nextSubmission = SubmissionModel(
                        id: UUID(),
                        caption: "Quiet lines.",
                        status: "published",
                        timerMode: "countdown",
                        timerSeconds: 300,
                        likeCount: 0,
                        reflectionCount: 0,
                        viewerHasLiked: false,
                        isOwner: true,
                        imageURL: URL(string: "https://example.test/display")!,
                        thumbnailURL: URL(string: "https://example.test/thumb")!,
                        username: "sketchy",
                        displayName: "Sketcher",
                        promptWords: ["Chocolate", "Coffee", "Banana"],
                        promptDate: Date(),
                        sketchSessionId: UUID(),
                        publishedAt: Date()
                    )
                    return repo
                }(),
                accessTokenProvider: { "token" }
            )
        )
    }
    .preferredColorScheme(.dark)
}
