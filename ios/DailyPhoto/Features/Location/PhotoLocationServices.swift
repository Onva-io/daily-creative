import Foundation

/// A WGS-84 position. Kept free of CoreLocation so the editor model and its
/// tests only need Foundation.
struct GeoCoordinate: Codable, Equatable, Sendable {
    var latitude: Double
    var longitude: Double

    var isValid: Bool {
        (-90...90).contains(latitude) && (-180...180).contains(longitude)
    }
}

/// Reads the position a picture was taken at from its own metadata.
protocol ImageLocationReading: Sendable {
    /// EXIF GPS position, or `nil` when the bytes carry none.
    func coordinate(in imageData: Data) -> GeoCoordinate?
}

/// One-shot "where is the device now".
protocol DeviceLocationProviding: Sendable {
    /// Asks for when-in-use permission when undetermined. `nil` when denied,
    /// restricted, unavailable or too slow.
    func currentLocation() async -> GeoCoordinate?
}

struct PlaceSearchResult: Identifiable, Equatable, Sendable {
    let id: UUID
    /// "Brighton Palace Pier"
    let name: String
    /// "Madeira Dr, Brighton", when the search backend has one.
    let detail: String?
    let coordinate: GeoCoordinate

    init(id: UUID = UUID(), name: String, detail: String?, coordinate: GeoCoordinate) {
        self.id = id
        self.name = name
        self.detail = detail
        self.coordinate = coordinate
    }
}

/// Free-text place lookup used to override the seeded position.
protocol PlaceSearching: Sendable {
    /// `near` biases results; it is not a filter.
    func search(_ query: String, near: GeoCoordinate?) async throws -> [PlaceSearchResult]
}

// MARK: - Test and preview doubles

struct FixedImageLocationReader: ImageLocationReading {
    var coordinate: GeoCoordinate?

    func coordinate(in imageData: Data) -> GeoCoordinate? {
        coordinate
    }
}

struct FixedDeviceLocationProvider: DeviceLocationProviding {
    var coordinate: GeoCoordinate?

    func currentLocation() async -> GeoCoordinate? {
        coordinate
    }
}

struct FixedPlaceSearcher: PlaceSearching {
    var results: [PlaceSearchResult] = []
    var error: Error?

    func search(_ query: String, near: GeoCoordinate?) async throws -> [PlaceSearchResult] {
        if let error { throw error }
        return results
    }
}
