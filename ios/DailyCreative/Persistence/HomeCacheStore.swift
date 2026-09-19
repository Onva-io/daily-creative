import Foundation

struct CachedHomeSnapshot: Codable, Equatable, Sendable {
    var prompt: DailyPromptModel?
    var feedItems: [FeedItemModel]
    var nextFeedCursor: String?
    var cachedAt: Date
}

protocol HomeCacheStoring: Sendable {
    func load() throws -> CachedHomeSnapshot?
    func save(_ snapshot: CachedHomeSnapshot) throws
    func clear() throws
}

struct HomeCacheStore: HomeCacheStoring {
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
        // Versioned: the unified-content FeedItemModel cannot decode caches
        // written by earlier builds, so those are removed rather than parsed.
        self.fileURL = directory.appendingPathComponent("home_cache_v2.json")
        let legacyURL = directory.appendingPathComponent("home_cache.json")
        if fileManager.fileExists(atPath: legacyURL.path) {
            try? fileManager.removeItem(at: legacyURL)
        }
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

    func load() throws -> CachedHomeSnapshot? {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return nil }
        let data = try Data(contentsOf: fileURL)
        if data.isEmpty { return nil }
        return try decoder.decode(CachedHomeSnapshot.self, from: data)
    }

    func save(_ snapshot: CachedHomeSnapshot) throws {
        let data = try encoder.encode(snapshot)
        try data.write(to: fileURL, options: [.atomic])
    }

    func clear() throws {
        if FileManager.default.fileExists(atPath: fileURL.path) {
            try FileManager.default.removeItem(at: fileURL)
        }
    }
}

final class InMemoryHomeCacheStore: HomeCacheStoring, @unchecked Sendable {
    private var snapshot: CachedHomeSnapshot?

    func load() throws -> CachedHomeSnapshot? {
        snapshot
    }

    func save(_ snapshot: CachedHomeSnapshot) throws {
        self.snapshot = snapshot
    }

    func clear() throws {
        snapshot = nil
    }
}
