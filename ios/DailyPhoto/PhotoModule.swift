import SwiftUI

/// Daily Photo: optional timer → take or pick a photograph → review with a
/// place → publish.
///
/// The shell, session, capture and review screens are shared with Daily
/// Sketch. What is photo-specific lives in `PhotoCapturePlugin`: reading the
/// picture's own location, letting the author correct and title it, and the
/// per-post choice of whether exact coordinates are published.
@MainActor
final class PhotoModule: CreativeModule {
    let creativeTypeID = "photo"

    let vocabulary = CreativeVocabulary(
        noun: "photo",
        nounPlural: "photos",
        nounCapitalized: "Photo",
        nounPluralCapitalized: "Photos",
        pastTenseVerb: "photographed",
        anotherActionTitle: "Take Another Photo",
        startingMessage: "Starting your photo…",
        inspirationSubtitle: "Tap a prompt, then go and find it through your lens.",
        emptyFeedSystemImage: "camera.on.rectangle"
    )

    let sessionLabels = TimedSessionLabels(
        activityCaps: "LOOKING…",
        activity: "Looking for your shot…",
        systemImage: "camera.viewfinder",
        continueTitle: "Take Photo",
        continueSystemImage: "camera",
        keepGoingTitle: "Keep Looking",
        cancelTitle: "End this photo session?",
        cancelMessage: "Nothing you have shot is affected, but this timer session will be marked as abandoned."
    )

    /// A photograph is usually taken when the moment comes, so the picker
    /// opens on "No timer"; the author can still choose one.
    let defaultTimerOption: TimerPreferenceOption? = .noTimer

    func makeHomeView() -> AnyView {
        CaptureModuleSupport.makeHomeView { _ in
            PhotoCapturePlugin(
                imageLocationReader: ImageIOLocationReader(),
                deviceLocationProvider: CoreLocationDeviceProvider(),
                placeSearcher: MapKitPlaceSearcher()
            )
        }
    }

    func makeGuestDraftCard(dependencies: AppDependencies) -> AnyView? {
        CaptureModuleSupport.makeGuestDraftCard(dependencies: dependencies)
    }
}
