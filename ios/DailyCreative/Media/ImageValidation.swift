import Foundation
import UIKit

enum ImageValidationError: LocalizedError, Equatable {
    case empty
    case undecodable
    case invalidDimensions
    case tooLarge(bytes: Int, limit: Int)

    var errorDescription: String? {
        switch self {
        case .empty:
            return "The selected image was empty."
        case .undecodable:
            return "That image couldn’t be opened. Try another photo."
        case .invalidDimensions:
            return "That image has invalid dimensions."
        case .tooLarge(let bytes, let limit):
            let mb = Double(bytes) / 1_048_576
            let limitMB = Double(limit) / 1_048_576
            return String(
                format: "That image is %.1f MB. Please choose one under %.0f MB.",
                mb,
                limitMB
            )
        }
    }
}

enum ImageValidation {
    /// Soft client-side ceiling before Phase 7 upload limits exist in OpenAPI.
    static let maxByteSize = 15 * 1_024 * 1_024
    static let jpegQuality: CGFloat = 0.85

    /// Normalizes orientation to `.up` and returns JPEG data suitable for a Draft.
    static func normalizedJPEGData(from image: UIImage, maxBytes: Int = maxByteSize) throws -> Data {
        let upright = image.normalizedUpOrientation()
        guard upright.size.width > 0, upright.size.height > 0 else {
            throw ImageValidationError.invalidDimensions
        }
        guard let data = upright.jpegData(compressionQuality: jpegQuality), !data.isEmpty else {
            throw ImageValidationError.undecodable
        }
        if data.count > maxBytes {
            throw ImageValidationError.tooLarge(bytes: data.count, limit: maxBytes)
        }
        return data
    }

    static func validatedImage(from data: Data) throws -> UIImage {
        guard !data.isEmpty else {
            throw ImageValidationError.empty
        }
        guard let image = UIImage(data: data) else {
            throw ImageValidationError.undecodable
        }
        guard image.size.width > 0, image.size.height > 0 else {
            throw ImageValidationError.invalidDimensions
        }
        return image
    }
}

extension UIImage {
    func normalizedUpOrientation() -> UIImage {
        guard imageOrientation != .up else { return self }
        let format = UIGraphicsImageRendererFormat.default()
        format.scale = scale
        let renderer = UIGraphicsImageRenderer(size: size, format: format)
        return renderer.image { _ in
            draw(in: CGRect(origin: .zero, size: size))
        }
    }
}
