import Foundation
import UIKit

#if canImport(SensitiveContentAnalysis)
import SensitiveContentAnalysis
#endif

/// On-device advisory screening before upload. Backend moderation always wins.
enum OnDeviceContentScreening {
    @MainActor
    static func mayContainSensitiveImage(_ image: UIImage) async -> Bool {
        #if canImport(SensitiveContentAnalysis)
        if #available(iOS 17.0, *) {
            // Prefer SCSensitivityAnalyzer when the framework is linked.
            // Until then, skip and rely on backend screening.
            _ = image
            return false
        }
        #endif
        _ = image
        return false
    }
}
