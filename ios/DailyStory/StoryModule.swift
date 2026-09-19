import SwiftUI

/// Daily Story: timer to think → write in the editor → publish.
///
/// The only story-specific screens are the writing editor and the Home tab
/// that wires it to the shared `HomeViewModel`; text drafts live in
/// `DraftTextStore`, so there is no guest draft card.
@MainActor
final class StoryModule: CreativeModule {
    let creativeTypeID = "story"

    let vocabulary = CreativeVocabulary(
        noun: "story",
        nounPlural: "stories",
        nounCapitalized: "Story",
        nounPluralCapitalized: "Stories",
        pastTenseVerb: "wrote",
        anotherActionTitle: "Write Another Story",
        startingMessage: "Starting your story…",
        inspirationSubtitle: "Tap a prompt to start writing your daily story.",
        emptyFeedSystemImage: "text.alignleft"
    )

    let sessionLabels = TimedSessionLabels(
        activityCaps: "THINKING…",
        activity: "Think about your story…",
        systemImage: "text.book.closed",
        continueTitle: "Start Writing",
        continueSystemImage: "pencil",
        keepGoingTitle: "Keep Thinking",
        cancelTitle: "End this story session?",
        cancelMessage: "This timer session will be marked as abandoned. Nothing you have written is affected."
    )

    let defaultTimerOption: TimerPreferenceOption? = nil

    func makeHomeView() -> AnyView {
        AnyView(StoryHomeView())
    }

    func makeGuestDraftCard(dependencies: AppDependencies) -> AnyView? {
        nil
    }
}
