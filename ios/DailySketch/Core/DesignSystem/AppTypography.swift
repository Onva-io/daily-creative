import SwiftUI

enum AppTypography {
    static let display = Font.system(size: 38, weight: .bold)
    static let title1 = Font.largeTitle.bold()
    static let title2 = Font.title.bold()
    static let title3 = Font.title2.weight(.semibold)
    static let headline = Font.headline
    static let bodyLarge = Font.body
    static let body = Font.body
    static let bodySmall = Font.subheadline
    static let caption = Font.caption
    static let labelCaps = Font.caption.weight(.semibold)
}
