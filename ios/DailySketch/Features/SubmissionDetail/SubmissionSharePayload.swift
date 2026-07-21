import Foundation
import UIKit

/// Builds a leak-free share payload for Submission Detail.
/// Never includes signed storage URLs or tokens.
struct SubmissionSharePayload: Equatable {
    let image: UIImage?
    let text: String

    var activityItems: [Any] {
        var items: [Any] = [text]
        if let image {
            items.insert(image, at: 0)
        }
        return items
    }

    static func make(
        promptWords: [String],
        displayName: String,
        username: String,
        image: UIImage?,
        body: String? = nil,
        publicLink: URL? = nil
    ) -> SubmissionSharePayload {
        let promptLine = promptWords.joined(separator: " · ")
        let kind = ProductConfig.current.creativeTypeID == "story" ? "story" : "sketch"
        var lines = [
            promptLine,
            "A \(kind) by \(displayName) (@\(username))",
        ]
        if let body, !body.isEmpty {
            let preview = body.count > 280 ? String(body.prefix(277)) + "…" : body
            lines.append(preview)
        }
        lines.append(ProductConfig.current.shareFooter)
        if let publicLink {
            lines.append(publicLink.absoluteString)
        }
        return SubmissionSharePayload(image: image, text: lines.joined(separator: "\n"))
    }

    /// True when the share text contains a signed-looking storage URL/query token.
    static func textContainsPrivateURL(_ text: String) -> Bool {
        let lowered = text.lowercased()
        if lowered.contains("x-amz-signature")
            || lowered.contains("x-amz-credential")
            || lowered.contains("x-amz-security-token")
            || lowered.contains("awsaccesskeyid=")
        {
            return true
        }
        // Match common signed-object path patterns without being overly broad on hostnames.
        if lowered.contains("/original?") || lowered.contains("/display?") || lowered.contains("/thumbnail?") {
            return true
        }
        return false
    }
}

enum SubmissionImageDownloader {
    static func downloadImage(from url: URL) async -> UIImage? {
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                return nil
            }
            return UIImage(data: data)
        } catch {
            return nil
        }
    }
}
