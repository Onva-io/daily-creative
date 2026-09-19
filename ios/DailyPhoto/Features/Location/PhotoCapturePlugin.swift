import Foundation
import Observation
import SwiftUI

/// Daily Photo's hooks into the shared capture pipeline: the image plus an
/// author-confirmed place.
@MainActor
final class PhotoCapturePlugin: CaptureContentPlugin {
    let captureInstructions = "Take a photo now, or choose one from your library."

    private let imageLocationReader: any ImageLocationReading
    private let deviceLocationProvider: any DeviceLocationProviding
    private let placeSearcher: any PlaceSearching

    init(
        imageLocationReader: any ImageLocationReading,
        deviceLocationProvider: any DeviceLocationProviding,
        placeSearcher: any PlaceSearching
    ) {
        self.imageLocationReader = imageLocationReader
        self.deviceLocationProvider = deviceLocationProvider
        self.placeSearcher = placeSearcher
    }

    func makeExtrasController(
        draft: LocalDraft,
        captured: CapturedImage?
    ) -> any CaptureExtrasControlling {
        PhotoLocationEditorModel(
            draft: draft,
            captured: captured,
            imageLocationReader: imageLocationReader,
            deviceLocationProvider: deviceLocationProvider,
            placeSearcher: placeSearcher
        )
    }
}

/// What Daily Photo stores in `LocalDraft.contentExtras`.
struct PhotoLocationDraft: Codable, Equatable, Sendable {
    var coordinate: GeoCoordinate?
    var label: String
    var source: PhotoLocationInputModel.Source?
    var shareExact: Bool
}

enum PhotoLocationLimits {
    /// Matches the API's `PhotoLocationInput.label` maximum.
    static let maxLabelLength = 120
}

/// The place attached to one photo while it is being reviewed.
///
/// Seeding order for a fresh image: the picture's own EXIF position, else the
/// device's current position, else nothing. Any of those can be replaced by a
/// search result or a pin on the map, and the author titles it themselves.
/// Exact coordinates are published only when `shareExact` is on; the default
/// is off and the toggle is unavailable until there are coordinates.
@MainActor
@Observable
final class PhotoLocationEditorModel: CaptureExtrasControlling {
    private(set) var coordinate: GeoCoordinate?
    private(set) var source: PhotoLocationInputModel.Source?
    private(set) var isSeeding = false

    var label: String {
        didSet {
            if label.count > PhotoLocationLimits.maxLabelLength {
                label = String(label.prefix(PhotoLocationLimits.maxLabelLength))
            }
        }
    }

    /// Only meaningful with coordinates; cleared whenever they go away.
    var shareExact: Bool {
        didSet {
            if shareExact, coordinate == nil {
                shareExact = false
            }
        }
    }

    var searchQuery = ""
    private(set) var searchResults: [PlaceSearchResult] = []
    private(set) var isSearching = false
    private(set) var searchErrorMessage: String?

    private let imageLocationReader: any ImageLocationReading
    private let deviceLocationProvider: any DeviceLocationProviding
    private let placeSearcher: any PlaceSearching
    private var seedingTask: Task<Void, Never>?

    init(
        draft: LocalDraft,
        captured: CapturedImage?,
        imageLocationReader: any ImageLocationReading,
        deviceLocationProvider: any DeviceLocationProviding,
        placeSearcher: any PlaceSearching
    ) {
        self.imageLocationReader = imageLocationReader
        self.deviceLocationProvider = deviceLocationProvider
        self.placeSearcher = placeSearcher
        self.label = ""
        self.shareExact = false

        if let extras = draft.contentExtras,
           let restored = try? JSONDecoder().decode(PhotoLocationDraft.self, from: extras) {
            coordinate = restored.coordinate
            label = restored.label
            source = restored.source
            shareExact = restored.coordinate != nil && restored.shareExact
        } else if let captured {
            seed(from: captured)
        }
    }

    var hasCoordinates: Bool {
        coordinate != nil
    }

    var hasLocation: Bool {
        hasCoordinates || !trimmedLabel.isEmpty
    }

    /// Where the current coordinates came from, for the author's benefit.
    var sourceDescription: String? {
        guard coordinate != nil else { return nil }
        switch source {
        case .exif: return "From the photo’s own location data."
        case .device: return "Your current location."
        case .search: return "Chosen from search."
        case .pin: return "Pinned on the map."
        case nil: return nil
        }
    }

    var sharingFootnote: String {
        if !hasCoordinates {
            return "Add a place title, search, or drop a pin. Nothing is shared until you publish."
        }
        return shareExact
            ? "Others will see this pin on a map."
            : "Others will only see your place title, never the pin."
    }

    // MARK: Seeding

    private func seed(from captured: CapturedImage) {
        seedingTask?.cancel()
        if let original = captured.originalData,
           let fromImage = imageLocationReader.coordinate(in: original) {
            apply(fromImage, source: .exif)
            return
        }
        isSeeding = true
        seedingTask = Task { [weak self] in
            let fix = await self?.deviceLocationProvider.currentLocation()
            guard let self, !Task.isCancelled else { return }
            self.isSeeding = false
            // The author may already have chosen something while we waited.
            guard self.coordinate == nil, let fix else { return }
            self.apply(fix, source: .device)
        }
    }

    func handleImageReplaced(_ captured: CapturedImage) {
        // Respect an explicit choice; only automatic seeds follow the image.
        switch source {
        case .search, .pin:
            return
        case .exif, .device, nil:
            coordinate = nil
            source = nil
            shareExact = false
            seed(from: captured)
        }
    }

    // MARK: Author overrides

    func runSearch() async {
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else {
            searchResults = []
            return
        }
        isSearching = true
        searchErrorMessage = nil
        defer { isSearching = false }
        do {
            searchResults = try await placeSearcher.search(query, near: coordinate)
            if searchResults.isEmpty {
                searchErrorMessage = "No places found for “\(query)”."
            }
        } catch {
            searchResults = []
            searchErrorMessage = "Couldn’t search right now. Try again, or drop a pin instead."
        }
    }

    func select(_ result: PlaceSearchResult) {
        apply(result.coordinate, source: .search)
        if trimmedLabel.isEmpty {
            label = result.name
        }
        searchResults = []
        searchQuery = ""
        searchErrorMessage = nil
    }

    func movePin(to newCoordinate: GeoCoordinate) {
        apply(newCoordinate, source: .pin)
    }

    func removeLocation() {
        seedingTask?.cancel()
        isSeeding = false
        coordinate = nil
        source = nil
        shareExact = false
        label = ""
        searchResults = []
        searchQuery = ""
        searchErrorMessage = nil
    }

    private func apply(_ newCoordinate: GeoCoordinate, source newSource: PhotoLocationInputModel.Source) {
        guard newCoordinate.isValid else { return }
        seedingTask?.cancel()
        isSeeding = false
        coordinate = newCoordinate
        source = newSource
    }

    private var trimmedLabel: String {
        label.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // MARK: CaptureExtrasControlling

    func encodeExtras() throws -> Data? {
        guard hasLocation else { return nil }
        return try JSONEncoder().encode(
            PhotoLocationDraft(
                coordinate: coordinate,
                label: trimmedLabel,
                source: source,
                shareExact: shareExact && hasCoordinates
            )
        )
    }

    func makeReviewView(isDisabled: Bool) -> AnyView? {
        AnyView(PhotoLocationEditorView(model: self, isDisabled: isDisabled))
    }

    func makePublicationContent(uploadId: UUID, caption: String?) -> PublicationContent {
        .photo(uploadId: uploadId, caption: caption, location: locationInput)
    }

    /// The payload the API receives, or `nil` when the author attached nothing.
    var locationInput: PhotoLocationInputModel? {
        guard hasLocation else { return nil }
        return PhotoLocationInputModel(
            latitude: coordinate?.latitude,
            longitude: coordinate?.longitude,
            label: trimmedLabel.isEmpty ? nil : trimmedLabel,
            source: coordinate == nil ? nil : source,
            shareExact: shareExact && hasCoordinates
        )
    }
}
