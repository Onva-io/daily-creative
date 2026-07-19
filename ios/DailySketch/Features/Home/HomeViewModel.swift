import Foundation
import Observation

enum HomePromptState: Equatable {
    case loading
    case loaded(DailyPromptModel)
    case missing
    case failed(String)
}

enum HomeFeedState: Equatable {
    case loading
    case empty
    case failed(String)
}

@MainActor
@Observable
final class HomeViewModel {
    private(set) var promptState: HomePromptState = .loading
    private(set) var feedState: HomeFeedState = .loading
    private(set) var cachedPrompt: DailyPromptModel?
    private(set) var todaysPublished: [PublishedLocalSubmission] = []

    private let promptFetcher: any PromptFetching
    private let feedFetcher: any FeedFetching
    private let publishedStore: any PublishedSubmissionStoring
    let sketchFlow: SketchFlowViewModel

    init(
        promptFetcher: any PromptFetching,
        feedFetcher: any FeedFetching,
        publishedStore: any PublishedSubmissionStoring,
        sketchFlow: SketchFlowViewModel
    ) {
        self.promptFetcher = promptFetcher
        self.feedFetcher = feedFetcher
        self.publishedStore = publishedStore
        self.sketchFlow = sketchFlow
    }

    var canStartSketch: Bool {
        if case .loaded = promptState {
            return true
        }
        return false
    }

    var hasSketchedToday: Bool {
        !todaysPublished.isEmpty
    }

    var loadedPrompt: DailyPromptModel? {
        if case .loaded(let prompt) = promptState {
            return prompt
        }
        return cachedPrompt
    }

    var promptWords: [String]? {
        loadedPrompt?.words
    }

    var promptAccessibilityLabel: String {
        loadedPrompt?.accessibilityLabel ?? "Today’s prompt is loading."
    }

    var primarySketchButtonTitle: String {
        hasSketchedToday ? "Create Another Sketch" : "Start Sketch"
    }

    var viewMySketchTitle: String {
        todaysPublished.count > 1 ? "View My Sketches" : "View My Sketch"
    }

    func load() async {
        sketchFlow.prepareOnAppear()
        refreshPublishedToday()
        async let promptLoad: Void = loadPrompt()
        async let feedLoad: Void = loadFeed()
        _ = await (promptLoad, feedLoad)
    }

    func refreshPublishedToday() {
        guard let prompt = loadedPrompt ?? cachedPrompt else {
            todaysPublished = []
            return
        }
        todaysPublished = (try? publishedStore.forPromptDate(prompt.promptDate)) ?? []
    }

    func retryPrompt() async {
        await loadPrompt()
    }

    func retryFeed() async {
        await loadFeed()
    }

    func startSketch() {
        guard let prompt = loadedPrompt else { return }
        sketchFlow.startSketch(prompt: prompt)
    }

    private func loadPrompt() async {
        if let cachedPrompt {
            promptState = .loaded(cachedPrompt)
        } else {
            promptState = .loading
        }

        do {
            let prompt = try await promptFetcher.fetchTodaysPrompt()
            cachedPrompt = prompt
            promptState = .loaded(prompt)
            refreshPublishedToday()
        } catch let error as PromptAPIError where error == .promptNotFound {
            cachedPrompt = nil
            promptState = .missing
            todaysPublished = []
        } catch {
            if cachedPrompt == nil {
                promptState = .failed(error.localizedDescription)
            }
        }
    }

    private func loadFeed() async {
        feedState = .loading
        do {
            _ = try await feedFetcher.fetchRecentFeed(cursor: nil, limit: 20)
            feedState = .empty
        } catch {
            feedState = .failed("Couldn’t load community sketches. Check your connection and try again.")
        }
    }
}
