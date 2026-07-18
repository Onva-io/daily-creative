import Foundation

protocol DraftImageStoring: Sendable {
    func write(_ data: Data) throws -> String
    func readData(fileName: String) throws -> Data
    func delete(fileName: String) throws
    func fileURL(for fileName: String) -> URL?
}

enum DraftImageStoreError: LocalizedError, Equatable {
    case emptyData
    case fileNotFound(String)
    case writeFailed

    var errorDescription: String? {
        switch self {
        case .emptyData:
            return "The sketch image data was empty."
        case .fileNotFound(let name):
            return "Draft image “\(name)” was not found."
        case .writeFailed:
            return "Couldn’t save the sketch image."
        }
    }
}

struct DraftImageStore: DraftImageStoring {
    private let directory: URL

    init(fileManager: FileManager = .default) {
        let root = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? fileManager.temporaryDirectory
        let directory = root
            .appendingPathComponent("DailySketch", isDirectory: true)
            .appendingPathComponent("Drafts", isDirectory: true)
        if !fileManager.fileExists(atPath: directory.path) {
            try? fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        }
        self.directory = directory
    }

    init(directory: URL, fileManager: FileManager = .default) {
        self.directory = directory
        if !fileManager.fileExists(atPath: directory.path) {
            try? fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        }
    }

    func write(_ data: Data) throws -> String {
        guard !data.isEmpty else {
            throw DraftImageStoreError.emptyData
        }
        let fileName = "\(UUID().uuidString).jpg"
        let url = directory.appendingPathComponent(fileName)
        do {
            try data.write(to: url, options: [.atomic])
            try FileManager.default.setAttributes(
                [.protectionKey: FileProtectionType.complete],
                ofItemAtPath: url.path
            )
        } catch {
            throw DraftImageStoreError.writeFailed
        }
        return fileName
    }

    func readData(fileName: String) throws -> Data {
        let url = directory.appendingPathComponent(fileName)
        guard FileManager.default.fileExists(atPath: url.path) else {
            throw DraftImageStoreError.fileNotFound(fileName)
        }
        return try Data(contentsOf: url)
    }

    func delete(fileName: String) throws {
        let url = directory.appendingPathComponent(fileName)
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        try FileManager.default.removeItem(at: url)
    }

    func fileURL(for fileName: String) -> URL? {
        let url = directory.appendingPathComponent(fileName)
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        return url
    }
}

final class InMemoryDraftImageStore: DraftImageStoring, @unchecked Sendable {
    private var files: [String: Data] = [:]

    func write(_ data: Data) throws -> String {
        guard !data.isEmpty else {
            throw DraftImageStoreError.emptyData
        }
        let fileName = "\(UUID().uuidString).jpg"
        files[fileName] = data
        return fileName
    }

    func readData(fileName: String) throws -> Data {
        guard let data = files[fileName] else {
            throw DraftImageStoreError.fileNotFound(fileName)
        }
        return data
    }

    func delete(fileName: String) throws {
        files.removeValue(forKey: fileName)
    }

    func fileURL(for fileName: String) -> URL? {
        files[fileName] == nil ? nil : URL(fileURLWithPath: "/tmp/\(fileName)")
    }

    func contains(_ fileName: String) -> Bool {
        files[fileName] != nil
    }
}
