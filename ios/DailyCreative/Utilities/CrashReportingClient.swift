import Foundation
import OSLog
import Sentry

enum CrashReportingClient {
    private static let logger = Logger(subsystem: "com.codebrewery.dailycreatives", category: "crash")

    static func start() {
        guard let dsn = Bundle.main.object(forInfoDictionaryKey: "SENTRY_DSN") as? String else {
            logger.info("Crash reporting disabled (no SENTRY_DSN)")
            return
        }
        let trimmed = dsn.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("http"), trimmed.contains("@") else {
            logger.info("Crash reporting disabled (SENTRY_DSN unset or placeholder)")
            return
        }
        SentrySDK.start { options in
            options.dsn = trimmed
            options.environment = AppEnvironment.current.kind.rawValue
            if let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String {
                options.releaseName = "\(version)"
            }
        }
        logger.info(
            "Crash reporting started environment=\(AppEnvironment.current.kind.rawValue, privacy: .public)"
        )
    }

    static func recordNonFatal(_ error: Error, context: [String: String] = [:]) {
        logger.error(
            "non_fatal error=\(String(describing: error), privacy: .public) context=\(String(describing: context), privacy: .public)"
        )
        SentrySDK.capture(error: error)
    }
}
