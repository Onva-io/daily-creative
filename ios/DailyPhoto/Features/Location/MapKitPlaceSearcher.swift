import Foundation
import MapKit

/// Free-text place lookup via `MKLocalSearch`. Results are offered to the
/// author to pick from; nothing is stored until they do.
struct MapKitPlaceSearcher: PlaceSearching {
    var maxResults = 8

    func search(_ query: String, near: GeoCoordinate?) async throws -> [PlaceSearchResult] {
        let request = MKLocalSearch.Request()
        request.naturalLanguageQuery = query
        request.resultTypes = [.pointOfInterest, .address]
        if let near {
            request.region = MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: near.latitude, longitude: near.longitude),
                span: MKCoordinateSpan(latitudeDelta: 0.5, longitudeDelta: 0.5)
            )
        }
        let response = try await MKLocalSearch(request: request).start()
        return response.mapItems.prefix(maxResults).compactMap { item in
            let coordinate = item.placemark.coordinate
            guard CLLocationCoordinate2DIsValid(coordinate) else { return nil }
            let name = item.name ?? item.placemark.title ?? query
            let detail = item.placemark.title.flatMap { $0 == name ? nil : $0 }
            return PlaceSearchResult(
                name: name,
                detail: detail,
                coordinate: GeoCoordinate(latitude: coordinate.latitude, longitude: coordinate.longitude)
            )
        }
    }
}
