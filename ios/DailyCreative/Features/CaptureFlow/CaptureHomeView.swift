import SwiftUI

/// Home tab for image-based creative types (sketch, photo).
///
/// Composes the shared `HomeViewModel` (prompt, feed, likes) with a
/// `CaptureFlowViewModel` supplied by the module. All type-specific copy
/// comes from `dependencies.module.vocabulary`.
struct CaptureHomeView: View {
    @Environment(AppDependencies.self) private var dependencies
    @Environment(\.scenePhase) private var scenePhase
    @State private var viewModel: HomeViewModel?
    @State private var flow: CaptureFlowViewModel?
    @State private var showsDiscardDraftConfirmation = false

    let makeFlow: @MainActor (AppDependencies) -> CaptureFlowViewModel

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
                let flow = makeFlow(dependencies)
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
    private func content(_ model: HomeViewModel, _ flow: CaptureFlowViewModel) -> some View {
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
                get: { flow.showsCaptureSource },
                set: { if !$0 { flow.dismissCaptureSource() } }
            )
        ) {
            CaptureSourceView(
                noun: vocabulary.noun,
                instructions: flow.plugin.captureInstructions,
                cameraAuthorizer: flow.cameraAuthorizerForCapture,
                onImage: { captured in
                    flow.handleCapturedImage(captured)
                },
                onCancel: {
                    flow.dismissCaptureSource()
                },
                onValidationError: { message in
                    flow.handleCaptureValidationError(message)
                }
            )
            .overlay(alignment: .bottom) {
                if let message = flow.captureValidationMessage {
                    Text(message)
                        .font(AppTypography.bodySmall)
                        .foregroundStyle(AppColors.danger)
                        .padding()
                        .background(AppColors.dangerSoft)
                        .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
                        .padding()
                }
            }
        }
        .fullScreenCover(
            isPresented: Binding(
                get: { flow.showsReviewSubmission },
                set: { newValue in
                    if !newValue, !flow.showsSaveYourCreativity, !flow.showsCaptureSource {
                        flow.handleReviewOutcome(.continueLater)
                    }
                }
            )
        ) {
            if let reviewModel = flow.reviewViewModel {
                ReviewSubmissionView(model: reviewModel, noun: vocabulary.noun)
                    .fullScreenCover(
                        isPresented: Binding(
                            get: { flow.showsSaveYourCreativity },
                            set: { if !$0 { flow.continueLaterFromCreativity() } }
                        )
                    ) {
                        SaveYourCreativityView(
                            thumbnail: reviewModel.previewImage,
                            vocabulary: vocabulary,
                            onCreateAccount: { flow.presentCreateAccountFromCreativity() },
                            onSignIn: { flow.presentSignInFromCreativity() },
                            onContinueLater: { flow.continueLaterFromCreativity() }
                        )
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
                                            Button("Close") {
                                                flow.showsAuthSheet = false
                                            }
                                        }
                                    }
                            }
                            .environment(dependencies)
                            .onChange(of: dependencies.auth.isAuthenticated) { _, isAuthenticated in
                                if isAuthenticated {
                                    flow.handleAuthenticationCompleted()
                                }
                            }
                        }
                    }
            }
        }
        .onChange(of: flow.needsProfileCompletionPresentation) { _, needsPresentation in
            guard needsPresentation else { return }
            dependencies.navigation.resumePublicationAfterProfileCompletion = true
            dependencies.navigation.presentProfileCompletion(preferHome: true)
            flow.acknowledgeProfileCompletionPresentation()
        }
        .onChange(of: dependencies.navigation.publishResumeRequested) { _, requested in
            guard requested else { return }
            dependencies.navigation.publishResumeRequested = false
            flow.resumePendingPublishIfNeeded()
        }
        .onChange(of: flow.lastPublishedSubmissionId) { _, _ in
            model.refreshPublishedToday()
            Task { await model.retryFeed() }
        }
        .confirmationDialog(
            "Discard this draft?",
            isPresented: $showsDiscardDraftConfirmation,
            titleVisibility: .visible
        ) {
            Button("Discard", role: .destructive) {
                flow.discardDraft()
            }
            Button("Keep Draft", role: .cancel) {}
        } message: {
            Text("This removes the local image from this device.")
        }
    }

    private func inspirationSection(_ model: HomeViewModel, _ flow: CaptureFlowViewModel) -> some View {
        VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
            HomeSections.Header(model: model, vocabulary: vocabulary)

            if flow.showsRecoveryBanner {
                recoveryBanner(model, flow)
            }

            if flow.changeTimerHintVisible {
                changeTimerHint(flow)
            }

            if let message = flow.syncBannerMessage {
                Text(message)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
            }

            if let message = flow.draftSavedBanner {
                Text(message)
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

            if let draft = flow.recoverableDraft {
                DraftCardView(
                    draft: draft,
                    thumbnail: flow.recoverableDraftThumbnail,
                    onContinue: { flow.reopenDraft(draft) },
                    onDiscard: { showsDiscardDraftConfirmation = true }
                )
            }
        }
    }

    private func recoveryBanner(_ model: HomeViewModel, _ flow: CaptureFlowViewModel) -> some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("You have a \(vocabulary.noun) in progress")
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)
            HStack(spacing: AppSpacing.contentGap) {
                PrimaryButton(
                    title: "Resume",
                    action: {
                        flow.resumeRecoverableSession { id in
                            if let loaded = model.loadedPrompt, loaded.id == id {
                                return loaded
                            }
                            return model.cachedPrompt
                        }
                    }
                )
                SecondaryButton(
                    title: "Discard",
                    action: { flow.discardRecoverableSession() }
                )
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.large, style: .continuous))
    }

    private func changeTimerHint(_ flow: CaptureFlowViewModel) -> some View {
        HStack {
            Text("Using your remembered timer.")
                .font(AppTypography.bodySmall)
                .foregroundStyle(AppColors.textSecondary)
            Spacer()
            Button("Change next time") {
                flow.changeTimerNextTime()
            }
            .font(AppTypography.bodySmall)
            .foregroundStyle(AppColors.primary)
        }
    }
}

#Preview("Loading") {
    NavigationStack {
        PreviewCreativeModule().makeHomeView()
    }
    .environment(AppDependencies.preview)
}

#Preview("Dark") {
    NavigationStack {
        PreviewCreativeModule().makeHomeView()
    }
    .environment(AppDependencies.preview)
    .preferredColorScheme(.dark)
}
