import SwiftUI

/// Daily Sketch: timer → photograph your drawing → review → publish.
///
/// Everything here is copy plus `SketchCapturePlugin`; the shell, session,
/// capture and review screens are shared.
@MainActor
final class SketchModule: CreativeModule {
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

    /// Sketching is a timed practice; the picker opens with no preselection.
    let defaultTimerOption: TimerPreferenceOption? = nil

    func makeHomeView() -> AnyView {
        CaptureModuleSupport.makeHomeView { _ in SketchCapturePlugin() }
    }

    func makeGuestDraftCard(dependencies: AppDependencies) -> AnyView? {
        CaptureModuleSupport.makeGuestDraftCard(dependencies: dependencies)
    }
}
