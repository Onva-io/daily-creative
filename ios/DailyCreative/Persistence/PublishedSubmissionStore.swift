import Foundation

/// Local records of published submissions used for Home "You sketched today" until Phase 8 feed.
struct PublishedLocalSubmission: Codable, Equatable, Sendable, Identifiable {
    let id: UUID
    let promptId: UUID
    let promptDate: Date
    let timerMode: String
    let selectedTimerSeconds: Int?
    let caption: String?
    let publishedAt: Date
}

protocol PublishedSubmissionStoring: Sendable {
    func list() throws -> [PublishedLocalSubmission]
    func save(_ submission: PublishedLocalSubmission) throws
    func delete(id: UUID) throws
    func forPromptDate(_ promptDate: Date) throws -> [PublishedLocalSubmission]
}

struct PublishedSubmissionStore: PublishedSubmissionStoring {
    private let fileURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(fileManager: FileManager = .default) {
        let root = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? fileManager.temporaryDirectory
        let directory = root.appendingPathComponent("DailySketch", isDirectory: true)
        if !fileManager.fileExists(atPath: directory.path) {
            try? fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        }
        self.fileURL = directory.appendingPathComponent("published_submissions.json")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    init(fileURL: URL) {
        self.fileURL = fileURL
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    func list() throws -> [PublishedLocalSubmission] {
        try loadAll().sorted { $0.publishedAt > $1.publishedAt }
    }

    func save(_ submission: PublishedLocalSubmission) throws {
        var items = try loadAll()
        if let index = items.firstIndex(where: { $0.id == submission.id }) {
            items[index] = submission
        } else {
            items.append(submission)
        }
        try writeAll(items)
    }

    func delete(id: UUID) throws {
        var items = try loadAll()
        items.removeAll { $0.id == id }
        try writeAll(items)
    }

    func forPromptDate(_ promptDate: Date) throws -> [PublishedLocalSubmission] {
        let calendar = Calendar(identifier: .gregorian)
        return try list().filter {
            calendar.isDate($0.promptDate, inSameDayAs: promptDate)
        }
    }

    private func loadAll() throws -> [PublishedLocalSubmission] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return []
        }
        let data = try Data(contentsOf: fileURL)
        if data.isEmpty {
            return []
        }
        return try decoder.decode([PublishedLocalSubmission].self, from: data)
    }

    private func writeAll(_ items: [PublishedLocalSubmission]) throws {
        let data = try encoder.encode(items)
        try data.write(to: fileURL, options: [.atomic])
    }
}

final class InMemoryPublishedSubmissionStore: PublishedSubmissionStoring, @unchecked Sendable {
    private var items: [UUID: PublishedLocalSubmission] = [:]

    func list() throws -> [PublishedLocalSubmission] {
        Array(items.values).sorted { $0.publishedAt > $1.publishedAt }
    }

    func save(_ submission: PublishedLocalSubmission) throws {
        items[submission.id] = submission
    }

    func delete(id: UUID) throws {
        items.removeValue(forKey: id)
    }

    func forPromptDate(_ promptDate: Date) throws -> [PublishedLocalSubmission] {
        let calendar = Calendar(identifier: .gregorian)
        return try list().filter {
            calendar.isDate($0.promptDate, inSameDayAs: promptDate)
        }
    }
}
