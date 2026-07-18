import SwiftUI

enum AppShadows {
    static let color = Color.black.opacity(0.06)
    static let radius: CGFloat = 20
    static let yOffset: CGFloat = 8
}

extension View {
    func appSoftShadow() -> some View {
        shadow(
            color: AppShadows.color,
            radius: AppShadows.radius,
            x: 0,
            y: AppShadows.yOffset
        )
    }
}
