import SwiftUI

/// Community feed list shared by every app's Home tab. Items render from
/// their own `content`, so a mixed feed would still display correctly; the
/// vocabulary only shapes empty/error copy.
struct CommunityFeedSection: View {
    let model: HomeViewModel
    let vocabulary: CreativeVocabulary
    let onOpenSubmission: (UUID) -> Void
    let onOpenProfile: (_ username: String) -> Void

    var body: some View {
        switch model.feedState {
        case .loading:
            VStack(spacing: AppSpacing.contentGap) {
                LoadingSkeleton(height: 160)
                LoadingSkeleton(height: 160)
            }
            .accessibilityLabel("Loading community \(vocabulary.nounPlural)")

        case .empty:
            EmptyStateView(
                title: "No \(vocabulary.nounPlural) yet",
                message: "Be the first to share an interpretation of today’s prompt.",
                systemImage: vocabulary.emptyFeedSystemImage
            )

        case .loaded(let items):
            LazyVStack(spacing: AppSpacing.contentGapLarge) {
                ForEach(items) { item in
                    SubmissionCard(
                        item: item,
                        onTapArtwork: { onOpenSubmission(item.id) },
                        onTapOwner: { onOpenProfile(item.username) },
                        onTapLike: {
                            Task { await model.toggleLike(itemId: item.id) }
                        },
                        onTapReflection: { onOpenSubmission(item.id) }
                    )
                    .onAppear {
                        Task { await model.loadMoreFeedIfNeeded(currentItem: item) }
                    }
                }

                if model.isLoadingMoreFeed {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, AppSpacing.md)
                        .accessibilityLabel("Loading more \(vocabulary.nounPlural)")
                }
            }

        case .failed(let message):
            ErrorStateView(
                title: "Couldn’t load community \(vocabulary.nounPlural)",
                message: message,
                onRetry: { Task { await model.retryFeed() } }
            )
        }
    }
}
