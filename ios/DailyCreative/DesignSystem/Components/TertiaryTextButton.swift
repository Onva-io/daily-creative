import SwiftUI

struct TertiaryTextButton: View {
    let title: String
    let action: () -> Void
    var isDisabled: Bool = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.primary)
                .frame(minHeight: AppSpacing.minimumTouchTarget)
                .frame(maxWidth: .infinity)
        }
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.5 : 1)
        .accessibilityLabel(title)
    }
}

#Preview("Light") {
    TertiaryTextButton(title: "Save to Drafts") {}
        .padding()
        .background(AppColors.background)
        .preferredColorScheme(.light)
}

#Preview("Dark") {
    TertiaryTextButton(title: "Save to Drafts") {}
        .padding()
        .background(AppColors.background)
        .preferredColorScheme(.dark)
}
