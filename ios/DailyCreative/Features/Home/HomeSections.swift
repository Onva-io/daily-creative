import SwiftUI

/// Building blocks of every app's Home tab.
///
/// A module's home view composes these around its own flow-specific controls
/// (recovery banner, draft card, primary CTA…) so the prompt, offline state,
/// "published today" card and community feed look and behave identically in
/// every app.
enum HomeSections {
    /// Inspiration title, subtitle, offline indicator and prompt-refresh hint.
    struct Header: View {
        let model: HomeViewModel
        let vocabulary: CreativeVocabulary

        var body: some View {
            VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(model.loadedPrompt?.inspirationTitle ?? "Today’s Inspiration")
                        .font(AppTypography.display)
                        .foregroundStyle(AppColors.textPrimary)
                        .accessibilityIdentifier("inspiration-heading")

                    Text(vocabulary.inspirationSubtitle)
                        .font(AppTypography.bodyLarge)
                        .foregroundStyle(AppColors.textSecondary)
                }

                if let offlineMessage = model.offlineIndicatorMessage {
                    HStack(spacing: AppSpacing.sm) {
                        Image(systemName: "wifi.slash")
                            .foregroundStyle(AppColors.textSecondary)
                            .accessibilityHidden(true)
                        Text(offlineMessage)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textSecondary)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel(offlineMessage)
                }

                if model.isRefreshingPrompt {
                    HStack(spacing: AppSpacing.sm) {
                        ProgressView()
                            .controlSize(.small)
                        Text("Refreshing prompt…")
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.textTertiary)
                    }
                    .accessibilityLabel("Refreshing today’s prompt")
                }
            }
        }
    }

    /// Today's three words, or the loading/missing/failed state.
    struct Prompt: View {
        let model: HomeViewModel

        var body: some View {
            switch model.promptState {
            case .loading:
                LoadingSkeleton(height: PromptCardStackLayout.height)
                    .accessibilityLabel("Loading today’s prompt")

            case .loaded(let prompt):
                PromptCardStack(words: prompt.words, accessibilityLabel: prompt.accessibilityLabel)

            case .missing:
                ErrorStateView(
                    title: "Today’s prompt isn’t ready",
                    message: "Check back soon, or retry if you think this is temporary.",
                    onRetry: { Task { await model.retryPrompt() } }
                )

            case .failed(let message):
                ErrorStateView(
                    title: "Couldn’t load today’s prompt",
                    message: message,
                    onRetry: { Task { await model.retryPrompt() } }
                )
            }
        }
    }

    /// "You sketched today" card with a link to the user's own post.
    struct PublishedToday: View {
        let model: HomeViewModel
        let vocabulary: CreativeVocabulary
        let onViewMine: (UUID) -> Void

        var body: some View {
            VStack(alignment: .leading, spacing: AppSpacing.md) {
                HStack(spacing: AppSpacing.sm) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(AppColors.success)
                        .accessibilityHidden(true)
                    Text(vocabulary.publishedTodayTitle)
                        .font(AppTypography.headline)
                        .foregroundStyle(AppColors.textPrimary)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel(vocabulary.publishedTodayTitle)

                SecondaryButton(
                    title: vocabulary.viewMineTitle(count: model.todaysPublished.count),
                    action: {
                        if let first = model.todaysPublished.first {
                            onViewMine(first.id)
                        }
                    }
                )
                .accessibilityHint("Opens your published \(vocabulary.noun) for today")
            }
            .padding(AppSpacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(AppColors.surfaceSecondary)
            .clipShape(RoundedRectangle(cornerRadius: AppRadii.large, style: .continuous))
        }
    }

    /// Primary CTA: "Start Sketch" first, "Create Another Sketch" afterwards.
    struct StartButton: View {
        let model: HomeViewModel
        let vocabulary: CreativeVocabulary
        let isStarting: Bool
        let onStart: (DailyPromptModel) -> Void

        var body: some View {
            PrimaryButton(
                title: model.hasPublishedToday ? vocabulary.anotherActionTitle : ProductConfig.current.startActionTitle,
                action: {
                    guard let prompt = model.loadedPrompt else { return }
                    model.trackStartTapped(prompt: prompt)
                    onStart(prompt)
                },
                isDisabled: !model.canStartSession || isStarting,
                systemImage: model.hasPublishedToday ? "plus" : nil
            )
            .accessibilityHint(
                model.hasPublishedToday
                    ? "Starts another \(vocabulary.noun) for today’s prompt"
                    : "Starts today’s timed \(vocabulary.noun) session"
            )
        }
    }

    /// Community title, guest age gate, and the feed.
    struct Community: View {
        @Environment(AppDependencies.self) private var dependencies
        let model: HomeViewModel
        let vocabulary: CreativeVocabulary

        var body: some View {
            VStack(alignment: .leading, spacing: AppSpacing.contentGap) {
                Text(ProductConfig.current.communityTitle)
                    .font(AppTypography.title3)
                    .foregroundStyle(AppColors.textPrimary)

                if !dependencies.auth.isAuthenticated && !GuestAgeGateStore.shared.canBrowseCommunity {
                    GuestAgeGateView(store: GuestAgeGateStore.shared)
                        .frame(maxWidth: .infinity)
                        .frame(minHeight: 280)
                } else {
                    CommunityFeedSection(
                        model: model,
                        vocabulary: vocabulary,
                        onOpenSubmission: { id in
                            dependencies.navigation.homePath.append(.submissionDetail(id))
                        },
                        onOpenProfile: { username in
                            dependencies.navigation.homePath.append(.publicProfile(username: username))
                        }
                    )
                }
            }
        }
    }
}

extension View {
    /// Wires the presentation every Home tab shares: home-model auth sheet,
    /// like-error alert, network/scene refresh and cross-tab feed refresh.
    func homeTabBehaviors(model: HomeViewModel, dependencies: AppDependencies) -> some View {
        modifier(HomeTabBehaviors(model: model, dependencies: dependencies))
    }
}

private struct HomeTabBehaviors: ViewModifier {
    let model: HomeViewModel
    let dependencies: AppDependencies

    func body(content: Content) -> some View {
        content
            .onChange(of: dependencies.navigation.feedNeedsRefresh) { _, needsRefresh in
                guard needsRefresh else { return }
                dependencies.navigation.feedNeedsRefresh = false
                Task { await model.retryFeed() }
            }
            .sheet(
                isPresented: Binding(
                    get: { model.showsAuthSheet },
                    set: { model.showsAuthSheet = $0 }
                )
            ) {
                NavigationStack {
                    AuthenticationView(mode: model.authSheetMode)
                        .toolbar {
                            ToolbarItem(placement: .cancellationAction) {
                                Button("Close") {
                                    model.showsAuthSheet = false
                                }
                            }
                        }
                }
                .environment(dependencies)
                .onChange(of: dependencies.auth.isAuthenticated) { _, isAuthenticated in
                    if isAuthenticated {
                        Task { await model.handleAuthenticationCompleted() }
                    }
                }
            }
            .alert(
                "Couldn’t update Like",
                isPresented: Binding(
                    get: { model.likeErrorMessage != nil },
                    set: { if !$0 { model.clearLikeError() } }
                )
            ) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(model.likeErrorMessage ?? "")
            }
    }
}
