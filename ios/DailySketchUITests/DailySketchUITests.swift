import XCTest

final class DailySketchUITests: XCTestCase {
    func testLaunchShowsHomeAndProfileTabs() throws {
        let app = XCUIApplication()
        app.launch()

        let homeTab = app.tabBars.buttons["Home"]
        let profileTab = app.tabBars.buttons["Profile"]

        XCTAssertTrue(homeTab.waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Today’s Inspiration"].exists)

        XCTAssertTrue(profileTab.exists)
        profileTab.tap()
        XCTAssertTrue(app.staticTexts["Keep your creative history"].waitForExistence(timeout: 5))

        homeTab.tap()
        XCTAssertTrue(app.staticTexts["Today’s Inspiration"].waitForExistence(timeout: 5))
    }
}
