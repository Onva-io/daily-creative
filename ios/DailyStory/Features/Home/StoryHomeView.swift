import SwiftUI

/// Home tab for Daily Story.
///
/// Shares `HomeViewModel` and every `HomeSections` block with the other apps;
/// only the flow (timer → writing editor → publish) is story-specific.
struct StoryHomeView: View {
    @Environment(AppDependencies.self) private var dependencies
    @Environment(\.scenePhase) private var scenePhase
    @State private var viewModel: HomeViewModel?
    @State private var flow: StoryFlowViewModel?

    private var vocabulary: CreativeVocabulary { dependencies.module.vocabulary }

    var body: some View {
        Group {
            if let viewModel, let flow {
                content(viewModel, flow)
            } else {
                LoadingView(message: "Loading today’s inspiration…")
            }
        }
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle(ProductConfig.current.homeTitle)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if viewModel == nil {
                let flow = StoryFlowViewModel.make(dependencies: dependencies)
                self.flow = flow
                let model = HomeViewModel.make(dependencies: dependencies)
                viewModel = model
                flow.prepareOnAppear()
                await model.load()
            }
        }
        .onChange(of: dependencies.networkMonitor.isOnline) { _, _ in
            viewModel?.syncOfflineState()
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else { return }
            Task { await viewModel?.handleSceneBecameActive() }
        }
    }

    @ViewBuilder
    private func content(_ model: HomeViewModel, _ flow: StoryFlowViewModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppSpacing.section) {
                inspirationSection(model, flow)
                HomeSections.Community(model: model, vocabulary: vocabulary)
            }
            .padding(.horizontal, AppSpacing.screenHorizontal)
            .padding(.top, AppSpacing.md)
            .padding(.bottom, AppSpacing.section)
        }
        .refreshable {
            await model.refresh()
        }
        .homeTabBehaviors(model: model, dependencies: dependencies)
        .sheet(
            isPresented: Binding(
                get: { flow.showsTimerSelection },
                set: { if !$0 { flow.dismissTimerSelection() } }
            )
        ) {
            TimerSelectionView(
                selectedOption: Binding(
                    get: { flow.selectedTimerOption },
                    set: { flow.selectedTimerOption = $0 }
                ),
                rememberChoice: Binding(
                    get: { flow.rememberChoice },
                    set: { flow.rememberChoice = $0 }
                ),
                onStart: {
                    if let prompt = model.loadedPrompt {
                        flow.confirmTimerSelection(prompt: prompt)
                    }
                },
                onDismiss: { flow.dismissTimerSelection() },
                isStarting: flow.isCreatingSession
            )
        }
        .fullScreenCover(
            isPresented: Binding(
                get: { flow.showsActiveSession },
                set: { if !$0 { flow.handleSessionEnded() } }
            )
        ) {
            if let sessionModel = flow.sessionViewModel {
                TimedSessionView(model: sessionModel)
            }
        }
        .fullScreenCover(
            isPresented: Binding(
                get: { flow.showsWritingEditor },
                set: { flow.showsWritingEditor = $0 }
            )
        ) {
            StoryWritingView(
                text: Binding(
                    get: { flow.draftText },
                    set: { flow.draftText = $0 }
                ),
                promptWords: flow.promptWords,
                wordCount: flow.wordCount,
                onPublish: { flow.submitStory() },
                onSaveDraft: { flow.saveDraft() },
                isPublishing: flow.isPublishing
            )
        }
        .sheet(
            isPresented: Binding(
                get: { flow.showsAuthSheet },
                set: { flow.showsAuthSheet = $0 }
            )
        ) {
            NavigationStack {
                AuthenticationView(mode: flow.authSheetMode)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Close") { flow.showsAuthSheet = false }
                        }
                    }
            }
            .environment(dependencies)
        }
        .onChange(of: flow.lastPublishedSubmissionId) { _, _ in
            model.refreshPublishedToday()
            Task { await model.retryFeed() }
        }
        .alert(
            "Something went wrong",
            isPresented: Binding(
                get: { flow.errorMessage != nil },
                set: { if !$0 { flow.errorMessage = nil } }
            )
        ) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(flow.errorMessage ?? "")
        }
    }

    private func inspirationSection(_ model: HomeViewModel, _ flow: StoryFlowViewModel) -> some View {
        VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
            HomeSections.Header(model: model, vocabulary: vocabulary)

            if let banner = flow.draftSavedBanner {
                Text(banner)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.success)
            }

            HomeSections.Prompt(model: model)

            if model.hasPublishedToday {
                HomeSections.PublishedToday(model: model, vocabulary: vocabulary) { id in
                    dependencies.navigation.homePath.append(.submissionDetail(id))
                }
            }

            if flow.isCreatingSession {
                LoadingView(message: vocabulary.startingMessage)
            }

            HomeSections.StartButton(
                model: model,
                vocabulary: vocabulary,
                isStarting: flow.isCreatingSession
            ) { prompt in
                flow.start(prompt: prompt)
            }

            if !dependencies.auth.isAuthenticated {
                SecondaryButton(title: "Sign In") {
                    model.authSheetMode = .signIn
                    model.showsAuthSheet = true
                }
                .accessibilityLabel("Sign In")
            }
        }
    }
}
