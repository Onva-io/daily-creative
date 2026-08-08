import Foundation
@preconcurrency import DailyCreativeAPI

/// Thread-safe configuration for the shared OpenAPI client.
///
/// `DailyCreativeAPIAPI.customHeaders` is process-global. Concurrent repository
/// calls must not clear/set Authorization independently or they race (and can
/// strip auth from in-flight authenticated requests).
enum DailyCreativeAPIClientConfig {
    static func configure(baseURL: URL, accessToken: String? = nil) {
        var base = baseURL.absoluteString
        if base.hasSuffix("/") {
            base.removeLast()
        }
        DailyCreativeAPIAPI.basePath = base
        if let accessToken {
            DailyCreativeAPITokenBridge.setBearerToken(accessToken)
        }
        // When accessToken is nil, leave Authorization alone. Public endpoints
        // tolerate a bearer token; clearing it races with concurrent authed calls.
    }
}

enum DailyCreativeAPITokenBridge {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var _token: String?

    static func setBearerToken(_ token: String) {
        lock.lock()
        _token = token
        lock.unlock()
        // Assignment goes through the thread-safe customHeaders setter.
        var headers = DailyCreativeAPIAPI.customHeaders
        headers["Authorization"] = "Bearer \(token)"
        DailyCreativeAPIAPI.customHeaders = headers
    }

    static func clear() {
        lock.lock()
        _token = nil
        lock.unlock()
        var headers = DailyCreativeAPIAPI.customHeaders
        headers.removeValue(forKey: "Authorization")
        DailyCreativeAPIAPI.customHeaders = headers
    }

    static var currentToken: String? {
        lock.lock()
        defer { lock.unlock() }
        return _token
    }
}
