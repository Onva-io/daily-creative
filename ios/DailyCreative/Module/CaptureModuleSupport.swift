import SwiftUI

/// Shared building blocks for creative types whose flow is
/// timer → capture an image → review → publish (sketch, photo).
///
/// A module for such a type composes these instead of re-implementing the
/// Home tab, flow view model and guest draft card. The only type-specific
/// input is its `CaptureContentPlugin`.
@MainActor
enum CaptureModuleSupport {
    static func makeHomeView(plugin: @escaping @MainActor (AppDependencies) -> any CaptureContentPlugin) -> AnyView {
        AnyView(
            CaptureHomeView { dependencies in
                makeFlowViewModel(dependencies: dependencies, plugin: plugin(dependencies))
            }
        )
    }

    static func makeFlowViewModel(
        dependencies: AppDependencies,
        plugin: any CaptureContentPlugin,
        onPublishedToday: (() -> Void)? = nil
    ) -> CaptureFlowViewModel {
        CaptureFlowViewModel(
            creativeType: dependencies.module.creativeTypeID,
            sessionLabels: dependencies.module.sessionLabels,
            defaultTimerOption: dependencies.module.defaultTimerOption,
            plugin: plugin,
            auth: dependencies.auth,
            preferencesService: dependencies.preferencesService,
            guestTimerStore: dependencies.guestTimerPreferenceStore,
            activeSessionStore: dependencies.activeSessionStore,
            sessionService: dependencies.sessionRepository,
            draftStore: dependencies.draftStore,
            imageStore: dependencies.draftImageStore,
            cameraAuthorizer: dependencies.cameraAuthorizer,
            uploadService: dependencies.uploadRepository,
            submissionService: dependencies.submissionRepository,
            directUploader: dependencies.directUploader,
            publishedStore: dependencies.publishedSubmissionStore,
            analytics: dependencies.analytics,
            onPublishedToday: onPublishedToday
        )
    }

    static func makeGuestDraftCard(dependencies: AppDependencies) -> AnyView? {
        guard let draft = try? dependencies.draftStore.mostRecentRecoverable(),
              let data = try? dependencies.draftImageStore.readData(fileName: draft.imageFileName),
              let image = UIImage(data: data) else {
            return nil
        }
        return AnyView(
            DraftCardView(
                draft: draft,
                thumbnail: image,
                onContinue: {
                    dependencies.navigation.selectedTab = .home
                },
                onDiscard: {
                    try? dependencies.draftStore.delete(id: draft.id)
                    try? dependencies.draftImageStore.delete(fileName: draft.imageFileName)
                }
            )
        )
    }
}

/// Module used by SwiftUI previews and shared unit tests, where no App Store
/// target's module is available. Mirrors Daily Sketch.
@MainActor
final class PreviewCreativeModule: CreativeModule {
    let creativeTypeID = "sketch"

    let vocabulary = CreativeVocabulary(
        noun: "sketch",
        nounPlural: "sketches",
        nounCapitalized: "Sketch",
        nounPluralCapitalized: "Sketches",
        pastTenseVerb: "sketched",
        anotherActionTitle: "Create Another Sketch",
        startingMessage: "Starting your sketch…",
        inspirationSubtitle: "Tap a prompt to start your daily practice.",
        emptyFeedSystemImage: "photo.on.rectangle.angled"
    )

    let sessionLabels = TimedSessionLabels(
        activityCaps: "SKETCHING…",
        activity: "Sketching…",
        systemImage: "pencil.and.outline",
        continueTitle: "Take Photo",
        continueSystemImage: "camera",
        keepGoingTitle: "Keep Sketching",
        cancelTitle: "End this sketch session?",
        cancelMessage: "Your drawing will not be deleted, but this timer session will be marked as abandoned."
    )

    let defaultTimerOption: TimerPreferenceOption? = nil

    func makeHomeView() -> AnyView {
        CaptureModuleSupport.makeHomeView { _ in SketchCapturePlugin() }
    }

    func makeGuestDraftCard(dependencies: AppDependencies) -> AnyView? {
        CaptureModuleSupport.makeGuestDraftCard(dependencies: dependencies)
    }
}
