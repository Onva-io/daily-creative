import CoreLocation
import Foundation

/// One fix from CoreLocation's async update stream.
///
/// `liveUpdates()` prompts for when-in-use authorization itself when the
/// `NSLocationWhenInUseUsageDescription` key is present, so there is no
/// delegate dance. The stream is cancelled after the first usable position or
/// a definite refusal, and abandoned after `timeout` so the review screen is
/// never held hostage by a slow fix.
struct CoreLocationDeviceProvider: DeviceLocationProviding {
    var timeout: Duration = .seconds(12)

    func currentLocation() async -> GeoCoordinate? {
        await withTaskGroup(of: GeoCoordinate?.self) { group in
            group.addTask { await Self.firstFix() }
            group.addTask {
                try? await Task.sleep(for: timeout)
                return nil
            }
            let first = await group.next() ?? nil
            group.cancelAll()
            return first
        }
    }

    private static func firstFix() async -> GeoCoordinate? {
        do {
            for try await update in CLLocationUpdate.liveUpdates(.default) {
                if Task.isCancelled { return nil }
                if update.authorizationDenied
                    || update.authorizationDeniedGlobally
                    || update.authorizationRestricted
                    || update.locationUnavailable {
                    return nil
                }
                if let location = update.location {
                    let coordinate = GeoCoordinate(
                        latitude: location.coordinate.latitude,
                        longitude: location.coordinate.longitude
                    )
                    return coordinate.isValid ? coordinate : nil
                }
            }
        } catch {
            return nil
        }
        return nil
    }
}
