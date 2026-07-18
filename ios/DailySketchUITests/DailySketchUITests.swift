import XCTest

final class DailySketchUITests: XCTestCase {
    func testLaunchShowsHomeTab() throws {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["Home"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Today’s Inspiration"].exists)
    }
}
