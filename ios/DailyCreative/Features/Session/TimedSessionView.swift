import SwiftUI

/// Shared timer screen. All type-specific copy comes from `model.labels`.
struct TimedSessionView: View {
    @Bindable var model: TimedSessionViewModel

    private var labels: TimedSessionLabels { model.labels }

    var body: some View {
        ZStack {
            AppColors.background.ignoresSafeArea()

            VStack(spacing: AppSpacing.contentGapLarge) {
                Spacer(minLength: AppSpacing.lg)

                Image(systemName: labels.systemImage)
                    .font(.system(size: 28, weight: .regular))
                    .foregroundStyle(AppColors.textSecondary)
                    .accessibilityHidden(true)

                Text(labels.activityCaps)
                    .font(AppTypography.labelCaps)
                    .foregroundStyle(AppColors.textSecondary)
                    .tracking(1.2)

                if model.isCountdown {
                    Text(model.formattedCountdown)
                        .font(AppTypography.timer)
                        .foregroundStyle(AppColors.textPrimary)
                        .monospacedDigit()
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel("Time remaining")
                        .accessibilityValue(model.formattedCountdown)
                } else {
                    VStack(spacing: AppSpacing.sm) {
                        Text(labels.activity)
                            .font(AppTypography.title2)
                            .foregroundStyle(AppColors.textPrimary)
                        Text(model.formattedElapsed)
                            .font(AppTypography.title3.monospacedDigit())
                            .foregroundStyle(AppColors.textTertiary)
                            .accessibilityElement(children: .ignore)
                            .accessibilityLabel("Elapsed time")
                            .accessibilityValue(model.formattedElapsed)
                    }
                }

                DisclosureGroup {
                    PromptCardStack(
                        words: model.promptWords,
                        accessibilityLabel: model.promptAccessibilityLabel
                    )
                    .padding(.top, AppSpacing.sm)
                } label: {
                    Text("Today’s prompt")
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)
                }
                .tint(AppColors.textSecondary)
                .padding(.horizontal, AppSpacing.screenHorizontal)

                if model.syncPending, let message = model.syncErrorMessage {
                    Text(message)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textTertiary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, AppSpacing.screenHorizontal)
                }

                Spacer()

                controls
                    .padding(.horizontal, AppSpacing.screenHorizontal)
                    .padding(.bottom, AppSpacing.lg)
            }
        }
        .alert(
            labels.cancelTitle,
            isPresented: Binding(
                get: { model.showsCancelConfirmation },
                set: { if !$0 { model.dismissCancelConfirmation() } }
            )
        ) {
            Button(labels.keepGoingTitle, role: .cancel) {
                model.dismissCancelConfirmation()
            }
            Button("End Session", role: .destructive) {
                model.confirmCancel()
            }
        } message: {
            Text(labels.cancelMessage)
        }
        .onAppear {
            model.startTicking()
        }
        .onDisappear {
            model.stopTicking()
        }
    }

    @ViewBuilder
    private var controls: some View {
        switch model.phase {
        case .timerCompleted:
            VStack(spacing: AppSpacing.contentGap) {
                PrimaryButton(
                    title: labels.continueTitle,
                    action: { model.continueToNextStep() },
                    systemImage: labels.continueSystemImage
                )
                SecondaryButton(
                    title: labels.keepGoingTitle,
                    action: { model.keepGoingAfterTimer() }
                )
                SecondaryButton(
                    title: "Cancel",
                    action: { model.requestCancel() },
                    systemImage: "xmark"
                )
            }

        case .readyToContinue:
            VStack(spacing: AppSpacing.contentGap) {
                PrimaryButton(
                    title: labels.continueTitle,
                    action: { model.continueToNextStep() },
                    systemImage: labels.continueSystemImage
                )
                SecondaryButton(
                    title: "Cancel",
                    action: { model.requestCancel() },
                    systemImage: "xmark"
                )
            }

        case .paused:
            VStack(spacing: AppSpacing.contentGap) {
                PrimaryButton(
                    title: "Resume",
                    action: { model.resume() },
                    systemImage: "play.fill"
                )
                HStack(spacing: AppSpacing.contentGap) {
                    SecondaryButton(
                        title: "Finish",
                        action: { model.finish() },
                        systemImage: "checkmark"
                    )
                    SecondaryButton(
                        title: "Cancel",
                        action: { model.requestCancel() },
                        systemImage: "xmark"
                    )
                }
            }

        case .running:
            VStack(spacing: AppSpacing.contentGap) {
                if model.isCountdown {
                    PrimaryButton(
                        title: "Pause",
                        action: { model.pause() },
                        systemImage: "pause.fill"
                    )
                } else {
                    PrimaryButton(
                        title: "Finish",
                        action: { model.finish() },
                        systemImage: "checkmark"
                    )
                }
                HStack(spacing: AppSpacing.contentGap) {
                    if model.isCountdown {
                        SecondaryButton(
                            title: "Finish",
                            action: { model.finish() },
                            systemImage: "checkmark"
                        )
                    }
                    SecondaryButton(
                        title: "Cancel",
                        action: { model.requestCancel() },
                        systemImage: "xmark"
                    )
                }
            }

        case .abandoned:
            EmptyView()
        }
    }
}

@MainActor
private func previewSessionModel(
    timerOption: TimerPreferenceOption,
    syncPending: Bool = false
) -> TimedSessionViewModel {
    TimedSessionViewModel(
        creativeType: "sketch",
        labels: PreviewCreativeModule().sessionLabels,
        prompt: DailyPromptModel(
            id: UUID(),
            promptDate: Date(),
            word1: "Chocolate",
            word2: "Coffee",
            word3: "Banana",
            status: "published",
            publishedAt: Date()
        ),
        timerOption: timerOption,
        syncPending: syncPending,
        isGuest: !syncPending,
        postTimerStageEvent: "photo_step_reached",
        accessTokenProvider: { nil },
        sessionService: RecordingCreativeSessionRepository(),
        activeSessionStore: InMemoryActiveSessionStore(),
        onEnded: {}
    )
}

#Preview("Countdown") {
    TimedSessionView(model: previewSessionModel(timerOption: .fiveMinutes))
}

#Preview("No Timer Dark") {
    TimedSessionView(model: previewSessionModel(timerOption: .noTimer))
        .preferredColorScheme(.dark)
}

#Preview("Loading Sync") {
    TimedSessionView(
        model: {
            let model = previewSessionModel(timerOption: .oneMinute, syncPending: true)
            model.markSyncPending("Couldn’t reach the server. Keep going.")
            return model
        }()
    )
}
