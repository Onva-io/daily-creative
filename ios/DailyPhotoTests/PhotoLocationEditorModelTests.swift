import Foundation
import XCTest
@testable import DailyPhoto

@MainActor
final class PhotoLocationEditorModelTests: XCTestCase {
    private let brighton = GeoCoordinate(latitude: 50.8198, longitude: -0.1372)
    private let lisbon = GeoCoordinate(latitude: 38.7223, longitude: -9.1393)

    // MARK: Seeding

    func testSeedsFromImageMetadataBeforeDevice() {
        let model = makeModel(
            captured: CapturedImage(jpegData: Data([1]), originalData: Data([2]), source: .library),
            imageCoordinate: brighton,
            deviceCoordinate: lisbon
        )

        XCTAssertEqual(model.coordinate, brighton)
        XCTAssertEqual(model.source, .exif)
        XCTAssertFalse(model.isSeeding)
        XCTAssertEqual(model.sourceDescription, "From the photo’s own location data.")
    }

    func testFallsBackToDeviceLocationWhenImageHasNone() async {
        let model = makeModel(
            captured: CapturedImage(jpegData: Data([1]), originalData: Data([2]), source: .library),
            imageCoordinate: nil,
            deviceCoordinate: lisbon
        )

        XCTAssertTrue(model.isSeeding)
        await waitUntil(!model.isSeeding)
        XCTAssertEqual(model.coordinate, lisbon)
        XCTAssertEqual(model.source, .device)
    }

    func testCameraCaptureNeverReadsMetadataAndUsesDevice() async {
        let model = makeModel(
            captured: CapturedImage(jpegData: Data([1]), originalData: nil, source: .camera),
            imageCoordinate: brighton,
            deviceCoordinate: lisbon
        )

        await waitUntil(!model.isSeeding)
        XCTAssertEqual(model.coordinate, lisbon)
        XCTAssertEqual(model.source, .device)
    }

    func testNoSeedLeavesLocationEmptyAndSharingOff() async {
        let model = makeModel(
            captured: CapturedImage(jpegData: Data([1]), originalData: nil, source: .camera),
            imageCoordinate: nil,
            deviceCoordinate: nil
        )

        await waitUntil(!model.isSeeding)
        XCTAssertNil(model.coordinate)
        XCTAssertFalse(model.hasLocation)
        XCTAssertNil(model.locationInput)
        XCTAssertNil(try model.encodeExtras())
        model.shareExact = true
        XCTAssertFalse(model.shareExact, "Sharing exact coordinates needs coordinates.")
    }

    func testLateDeviceFixDoesNotOverrideAuthorChoice() async {
        let slowDevice = SlowDeviceLocationProvider(coordinate: lisbon)
        let model = makeModel(
            captured: CapturedImage(jpegData: Data([1]), originalData: nil, source: .camera),
            imageCoordinate: nil,
            deviceProvider: slowDevice
        )
        model.movePin(to: brighton)
        slowDevice.release()

        try? await Task.sleep(for: .milliseconds(50))
        XCTAssertEqual(model.coordinate, brighton)
        XCTAssertEqual(model.source, .pin)
        XCTAssertFalse(model.isSeeding)
    }

    // MARK: Overrides

    func testSearchSelectionSetsCoordinateAndDefaultTitle() async {
        let result = PlaceSearchResult(name: "Palace Pier", detail: "Brighton", coordinate: brighton)
        let model = makeModel(captured: nil, searchResults: [result])
        model.searchQuery = "pier"

        await model.runSearch()
        XCTAssertEqual(model.searchResults, [result])

        model.select(result)
        XCTAssertEqual(model.coordinate, brighton)
        XCTAssertEqual(model.source, .search)
        XCTAssertEqual(model.label, "Palace Pier")
        XCTAssertTrue(model.searchResults.isEmpty)
        XCTAssertEqual(model.searchQuery, "")
    }

    func testSearchSelectionKeepsAnExistingTitle() async {
        let result = PlaceSearchResult(name: "Palace Pier", detail: nil, coordinate: brighton)
        let model = makeModel(captured: nil, searchResults: [result])
        model.label = "Where we met"

        model.select(result)
        XCTAssertEqual(model.label, "Where we met")
    }

    func testSearchFailureReportsWithoutClearingLocation() async {
        let model = makeModel(
            captured: nil,
            searchError: URLError(.notConnectedToInternet)
        )
        model.movePin(to: brighton)
        model.searchQuery = "anything"

        await model.runSearch()
        XCTAssertNotNil(model.searchErrorMessage)
        XCTAssertEqual(model.coordinate, brighton)
    }

    func testLabelIsClampedToAPILimit() {
        let model = makeModel(captured: nil)
        model.label = String(repeating: "x", count: PhotoLocationLimits.maxLabelLength + 30)
        XCTAssertEqual(model.label.count, PhotoLocationLimits.maxLabelLength)
    }

    func testRemoveLocationClearsEverything() {
        let model = makeModel(captured: nil)
        model.movePin(to: brighton)
        model.label = "Pier"
        model.shareExact = true

        model.removeLocation()
        XCTAssertNil(model.coordinate)
        XCTAssertNil(model.source)
        XCTAssertEqual(model.label, "")
        XCTAssertFalse(model.shareExact)
        XCTAssertNil(model.locationInput)
    }

    // MARK: Image replacement

    func testReplacingImageReseedsAutomaticLocation() {
        let reader = SequencedImageLocationReader(coordinates: [brighton, lisbon])
        let model = makeModel(
            captured: CapturedImage(jpegData: Data([1]), originalData: Data([2]), source: .library),
            imageReader: reader
        )
        XCTAssertEqual(model.coordinate, brighton)
        XCTAssertEqual(model.source, .exif)
        model.shareExact = true

        model.handleImageReplaced(CapturedImage(jpegData: Data([3]), originalData: Data([4]), source: .library))
        XCTAssertEqual(model.coordinate, lisbon)
        XCTAssertEqual(model.source, .exif)
        XCTAssertFalse(model.shareExact, "A new place must be opted into again.")
    }

    func testReplacingImageKeepsAuthorChosenLocation() {
        let model = makeModel(captured: nil, imageCoordinate: lisbon)
        model.movePin(to: brighton)
        model.shareExact = true

        model.handleImageReplaced(CapturedImage(jpegData: Data([3]), originalData: Data([4]), source: .library))
        XCTAssertEqual(model.coordinate, brighton)
        XCTAssertEqual(model.source, .pin)
        XCTAssertTrue(model.shareExact)
    }

    // MARK: Persistence and payload

    func testExtrasRoundTripThroughDraft() throws {
        let model = makeModel(captured: nil)
        model.movePin(to: brighton)
        model.label = "  Palace Pier  "
        model.shareExact = true

        let extras = try XCTUnwrap(model.encodeExtras())
        var draft = makeDraft()
        draft.contentExtras = extras

        let restored = makeModel(draft: draft, captured: nil, deviceCoordinate: lisbon)
        XCTAssertEqual(restored.coordinate, brighton)
        XCTAssertEqual(restored.source, .pin)
        XCTAssertEqual(restored.label, "Palace Pier")
        XCTAssertTrue(restored.shareExact)
        XCTAssertFalse(restored.isSeeding, "A restored draft must not be re-seeded from the device.")
    }

    func testRestoredExtrasWithoutCoordinatesCannotShareExact() throws {
        let extras = try JSONEncoder().encode(
            PhotoLocationDraft(coordinate: nil, label: "Somewhere", source: nil, shareExact: true)
        )
        var draft = makeDraft()
        draft.contentExtras = extras

        let restored = makeModel(draft: draft, captured: nil)
        XCTAssertFalse(restored.shareExact)
        XCTAssertEqual(restored.locationInput?.shareExact, false)
    }

    func testPublicationPayloadCarriesLocationAndSharingChoice() {
        let model = makeModel(captured: nil)
        let uploadId = UUID()

        model.movePin(to: brighton)
        model.label = "Pier"
        guard case .photo(let id, let caption, let location) = model.makePublicationContent(
            uploadId: uploadId,
            caption: "Salt air"
        ) else {
            return XCTFail("Expected a photo payload")
        }
        XCTAssertEqual(id, uploadId)
        XCTAssertEqual(caption, "Salt air")
        XCTAssertEqual(location?.latitude, brighton.latitude)
        XCTAssertEqual(location?.longitude, brighton.longitude)
        XCTAssertEqual(location?.label, "Pier")
        XCTAssertEqual(location?.source, .pin)
        XCTAssertEqual(location?.shareExact, false, "Exact sharing is off unless the author turns it on.")

        model.shareExact = true
        XCTAssertEqual(model.locationInput?.shareExact, true)
    }

    func testLabelOnlyLocationHasNoSourceAndNeverSharesExact() {
        let model = makeModel(captured: nil)
        model.label = "Somewhere quiet"

        let input = model.locationInput
        XCTAssertNil(input?.latitude)
        XCTAssertNil(input?.source)
        XCTAssertEqual(input?.label, "Somewhere quiet")
        XCTAssertEqual(input?.shareExact, false)
    }

    // MARK: Helpers

    private func makeModel(
        draft: LocalDraft? = nil,
        captured: CapturedImage?,
        imageCoordinate: GeoCoordinate? = nil,
        deviceCoordinate: GeoCoordinate? = nil,
        imageReader: (any ImageLocationReading)? = nil,
        deviceProvider: (any DeviceLocationProviding)? = nil,
        searchResults: [PlaceSearchResult] = [],
        searchError: Error? = nil
    ) -> PhotoLocationEditorModel {
        PhotoLocationEditorModel(
            draft: draft ?? makeDraft(),
            captured: captured,
            imageLocationReader: imageReader ?? FixedImageLocationReader(coordinate: imageCoordinate),
            deviceLocationProvider: deviceProvider ?? FixedDeviceLocationProvider(coordinate: deviceCoordinate),
            placeSearcher: FixedPlaceSearcher(results: searchResults, error: searchError)
        )
    }

    private func makeDraft() -> LocalDraft {
        LocalDraft(
            id: UUID(),
            localSessionId: UUID(),
            serverSessionId: nil,
            creativeType: "photo",
            promptId: UUID(),
            promptWords: ["Salt", "Light", "Iron"],
            promptAccessibilityLabel: "Today’s prompt: Salt, Light, Iron.",
            promptDate: Date(timeIntervalSince1970: 1_784_332_800),
            timerMode: "no_timer",
            selectedTimerSeconds: nil,
            sessionStartedAt: Date(timeIntervalSince1970: 1_784_332_800),
            imageFileName: "photo.jpg",
            caption: nil,
            createdAt: Date(timeIntervalSince1970: 1_784_332_800),
            updatedAt: Date(timeIntervalSince1970: 1_784_332_800),
            pendingAuthentication: false,
            pendingPublication: false
        )
    }

    private func waitUntil(_ condition: @autoclosure () -> Bool, timeout: TimeInterval = 2) async {
        let deadline = Date().addingTimeInterval(timeout)
        while !condition(), Date() < deadline {
            await Task.yield()
        }
    }
}

/// Returns each coordinate in turn, one per image read.
private final class SequencedImageLocationReader: ImageLocationReading, @unchecked Sendable {
    private var coordinates: [GeoCoordinate?]
    private let lock = NSLock()

    init(coordinates: [GeoCoordinate?]) {
        self.coordinates = coordinates
    }

    func coordinate(in imageData: Data) -> GeoCoordinate? {
        lock.lock()
        defer { lock.unlock() }
        return coordinates.isEmpty ? nil : coordinates.removeFirst()
    }
}

/// Holds the fix until `release()` so tests can act while seeding is pending.
private final class SlowDeviceLocationProvider: DeviceLocationProviding, @unchecked Sendable {
    private let coordinate: GeoCoordinate
    private var continuations: [CheckedContinuation<Void, Never>] = []
    private var released = false
    private let lock = NSLock()

    init(coordinate: GeoCoordinate) {
        self.coordinate = coordinate
    }

    func release() {
        lock.lock()
        released = true
        let waiting = continuations
        continuations = []
        lock.unlock()
        waiting.forEach { $0.resume() }
    }

    func currentLocation() async -> GeoCoordinate? {
        await withCheckedContinuation { continuation in
            lock.lock()
            if released {
                lock.unlock()
                continuation.resume()
            } else {
                continuations.append(continuation)
                lock.unlock()
            }
        }
        return coordinate
    }
}
