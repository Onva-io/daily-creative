import SwiftUI
import UIKit

enum AppColors {
    static let background = Color(light: "FFF8F3", dark: "1C1A18")
    static let surfacePrimary = Color(light: "FFFFFF", dark: "26231F")
    static let surfaceSecondary = Color(light: "FAF2EC", dark: "2E2A26")
    static let surfaceTertiary = Color(light: "F4ECE7", dark: "37322D")
    static let textPrimary = Color(light: "1E1B18", dark: "F7EFE9")
    static let textSecondary = Color(light: "5F5E5B", dark: "CBC4BE")
    static let textTertiary = Color(light: "76786F", dark: "A9A29C")
    static let primary = Color(light: "585E4C", dark: "C3C9B2")
    static let primaryPressed = Color(light: "434937", dark: "AAB19B")
    static let primarySoft = Color(light: "DFE5CD", dark: "434937")
    static let onPrimary = Color(light: "FFFFFF", dark: "181D0F")
    static let divider = Color(light: "E0D9D3", dark: "46413C")
    static let danger = Color(light: "BA1A1A", dark: "FFB4AB")
}

private extension Color {
    init(light: String, dark: String) {
        self.init(
            uiColor: UIColor { traits in
                let hex = traits.userInterfaceStyle == .dark ? dark : light
                return UIColor(hex: hex)
            }
        )
    }
}

private extension UIColor {
    convenience init(hex: String) {
        let cleaned = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var value: UInt64 = 0
        Scanner(string: cleaned).scanHexInt64(&value)
        let red = CGFloat((value >> 16) & 0xFF) / 255
        let green = CGFloat((value >> 8) & 0xFF) / 255
        let blue = CGFloat(value & 0xFF) / 255
        self.init(red: red, green: green, blue: blue, alpha: 1)
    }
}
