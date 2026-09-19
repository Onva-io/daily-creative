import Foundation
import ImageIO

/// Reads the EXIF GPS block with ImageIO. Runs on the picker's original bytes;
/// the normalised JPEG the app keeps has no metadata left to read.
struct ImageIOLocationReader: ImageLocationReading {
    func coordinate(in imageData: Data) -> GeoCoordinate? {
        guard let source = CGImageSourceCreateWithData(imageData as CFData, nil),
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let gps = properties[kCGImagePropertyGPSDictionary] as? [CFString: Any],
              let latitude = gps[kCGImagePropertyGPSLatitude] as? Double,
              let longitude = gps[kCGImagePropertyGPSLongitude] as? Double else {
            return nil
        }
        // EXIF stores unsigned magnitudes plus a hemisphere letter.
        let latitudeRef = (gps[kCGImagePropertyGPSLatitudeRef] as? String)?.uppercased()
        let longitudeRef = (gps[kCGImagePropertyGPSLongitudeRef] as? String)?.uppercased()
        let signedLatitude = latitudeRef == "S" ? -abs(latitude) : latitude
        let signedLongitude = longitudeRef == "W" ? -abs(longitude) : longitude
        let coordinate = GeoCoordinate(latitude: signedLatitude, longitude: signedLongitude)
        // (0, 0) is the classic "GPS block present but never filled in" value.
        guard coordinate.isValid, !(coordinate.latitude == 0 && coordinate.longitude == 0) else {
            return nil
        }
        return coordinate
    }
}
