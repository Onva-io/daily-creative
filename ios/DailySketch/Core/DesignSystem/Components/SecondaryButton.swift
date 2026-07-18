import SwiftUI

struct SecondaryButton: View {
    let title: String
    let action: () -> Void
    var isDisabled: Bool = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)
                .frame(maxWidth: .infinity)
                .frame(height: AppSpacing.controlHeight)
                .background(AppColors.surfaceTertiary)
                .clipShape(RoundedRectangle(cornerRadius: AppRadii.large, style: .continuous))
        }
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.5 : 1)
        .accessibilityLabel(title)
    }
}

#Preview("Light") {
    SecondaryButton(title: "Sign In") {}
        .padding()
        .background(AppColors.background)
        .preferredColorScheme(.light)
}

#Preview("Dark") {
    SecondaryButton(title: "Sign In") {}
        .padding()
        .background(AppColors.background)
        .preferredColorScheme(.dark)
}
