import XCTest
@testable import DailySketch

final class AppEnvironmentTests: XCTestCase {
    func testLocalEnvironmentDefaultsToLocalhost() {
        let environment = AppEnvironment(
            kind: .local,
            apiBaseURL: URL(string: "http://localhost:8000")!,
            descopeProjectID: "replace-me"
        )
        XCTAssertEqual(environment.kind, .local)
        XCTAssertEqual(environment.apiBaseURL.host, "localhost")
        XCTAssertEqual(environment.apiBaseURL.port, 8000)
        XCTAssertEqual(environment.descopeProjectID, "replace-me")
    }

    func testAllowsMockAuthenticationOnlyForLocalAndDevelopment() {
        XCTAssertTrue(AppEnvironment.Kind.local.allowsMockAuthentication)
        XCTAssertTrue(AppEnvironment.Kind.development.allowsMockAuthentication)
        XCTAssertFalse(AppEnvironment.Kind.staging.allowsMockAuthentication)
        XCTAssertFalse(AppEnvironment.Kind.production.allowsMockAuthentication)
    }

    func testIsPlaceholderProjectID() {
        XCTAssertTrue(DescopeConfig.isPlaceholderProjectID(""))
        XCTAssertTrue(DescopeConfig.isPlaceholderProjectID("   "))
        XCTAssertTrue(DescopeConfig.isPlaceholderProjectID("replace-me"))
        XCTAssertTrue(DescopeConfig.isPlaceholderProjectID("replace-me-production"))
        XCTAssertTrue(DescopeConfig.isPlaceholderProjectID("replace-me-development"))
        XCTAssertFalse(DescopeConfig.isPlaceholderProjectID("P3GtbG5aJKoUuefcaA8DfyMzA0nK"))
    }
}
