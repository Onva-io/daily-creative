import SwiftUI

/// Words the shared UI needs when it talks about *this app's* creative type.
///
/// Rendering of published work never uses this; it is driven by the
/// `SubmissionContentModel` of each item so mixed content stays correct.
struct CreativeVocabulary: Equatable, Sendable {
    /// "sketch"
    let noun: String
    /// "sketches"
    let nounPlural: String
    /// "Sketch"
    let nounCapitalized: String
    /// "Sketches"
    let nounPluralCapitalized: String
    /// "sketched" → "You sketched today"
    let pastTenseVerb: String
    /// "Create Another Sketch"
    let anotherActionTitle: String
    /// "Starting your sketch…"
    let startingMessage: String
    /// "Tap a prompt to start your daily practice."
    let inspirationSubtitle: String
    /// SF Symbol for the empty community feed.
    let emptyFeedSystemImage: String

    var publishedTodayTitle: String { "You \(pastTenseVerb) today" }

    func viewMineTitle(count: Int) -> String {
        count > 1 ? "View My \(nounPluralCapitalized)" : "View My \(nounCapitalized)"
    }

    func countLabel(_ count: Int) -> String {
        count == 1 ? "1 \(noun)" : "\(count) \(nounPlural)"
    }
}

/// Copy for the shared timed-session screen (`TimedSessionView`).
struct TimedSessionLabels: Equatable, Sendable {
    /// "SKETCHING…"
    let activityCaps: String
    /// "Sketching…"
    let activity: String
    /// SF Symbol shown above the clock.
    let systemImage: String
    /// "Take Photo"
    let continueTitle: String
    let continueSystemImage: String
    /// "Keep Sketching"
    let keepGoingTitle: String
    /// "End this sketch session?"
    let cancelTitle: String
    let cancelMessage: String
}

/// Everything one app contributes to the shared shell.
///
/// The shell (`AppDependencies`, `RootTabView`, profile, settings, detail,
/// feed rendering) is identical across apps and never branches on the type.
/// Each App Store target conforms exactly one module and hands it to
/// `AppDependencies.live(module:)`.
@MainActor
protocol CreativeModule: AnyObject {
    /// API `creative_type` discriminator for this app. Must match the
    /// `CREATIVE_TYPE_ID` the target's xcconfig writes into Info.plist.
    var creativeTypeID: String { get }
    var vocabulary: CreativeVocabulary { get }
    var sessionLabels: TimedSessionLabels { get }
    /// Timer option preselected when nothing is remembered. `nil` shows the
    /// picker with no selection so the user must choose.
    var defaultTimerOption: TimerPreferenceOption? { get }
    /// Root of the Home tab. Reads `AppDependencies` from the environment.
    func makeHomeView() -> AnyView
    /// Optional card shown to signed-out users on the Profile tab when there
    /// is local unpublished work worth keeping. Return `nil` when the type has
    /// no local drafts.
    func makeGuestDraftCard(dependencies: AppDependencies) -> AnyView?
}
