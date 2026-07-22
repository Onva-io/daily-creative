import UIKit
import XCTest
@testable import DailySketch

final class SubmissionSharePayloadTests: XCTestCase {
    func testPayloadIncludesPromptAttributionAndBrandingWithoutPrivateURL() {
        let image = UIImage(systemName: "photo")
        let payload = SubmissionSharePayload.make(
            promptWords: ["Chocolate", "Coffee", "Banana"],
            displayName: "Matt",
            username: "sketchy_matt",
            image: image,
            publicLink: nil
        )

        XCTAssertTrue(payload.text.contains("Chocolate · Coffee · Banana"))
        XCTAssertTrue(payload.text.contains("A sketch by Matt (@sketchy_matt)"))
        XCTAssertTrue(payload.text.contains(ProductConfig.current.shareFooter))
        XCTAssertFalse(SubmissionSharePayload.textContainsPrivateURL(payload.text))
        XCTAssertEqual(payload.activityItems.count, 2)
    }

    func testPrivateSignedURLDetector() {
        let leaky = "https://storage.example/users/1/uploads/2/display?X-Amz-Signature=abc"
        XCTAssertTrue(SubmissionSharePayload.textContainsPrivateURL(leaky))
        XCTAssertFalse(
            SubmissionSharePayload.textContainsPrivateURL("Shared via Daily Sketch")
        )
    }
}

final class EditProfileUsernameValidationTests: XCTestCase {
    func testUsernameValidatorRules() {
        XCTAssertNil(UsernameValidator.validationMessage(for: "valid_name"))
        XCTAssertNotNil(UsernameValidator.validationMessage(for: "ab"))
        XCTAssertNotNil(UsernameValidator.validationMessage(for: "bad-name!"))
        XCTAssertTrue(UsernameValidator.isValidFormat("sketchy_matt"))
        XCTAssertFalse(UsernameValidator.isValidFormat("no spaces"))
    }
}
