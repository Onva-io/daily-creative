import Foundation

protocol DraftTextStoring: Sendable {
    func saveDraft(_ text: String, forSessionId sessionId: UUID)
    func loadDraft(forSessionId sessionId: UUID) -> String?
    func deleteDraft(forSessionId sessionId: UUID)
}

final class DraftTextStore: DraftTextStoring, @unchecked Sendable {
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func saveDraft(_ text: String, forSessionId sessionId: UUID) {
        defaults.set(text, forKey: draftKey(sessionId))
    }

    func loadDraft(forSessionId sessionId: UUID) -> String? {
        defaults.string(forKey: draftKey(sessionId))
    }

    func deleteDraft(forSessionId sessionId: UUID) {
        defaults.removeObject(forKey: draftKey(sessionId))
    }

    private func draftKey(_ sessionId: UUID) -> String {
        "story_draft_\(sessionId.uuidString)"
    }
}
