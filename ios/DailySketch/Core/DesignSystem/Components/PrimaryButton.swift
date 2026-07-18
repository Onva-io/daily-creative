import SwiftUI

struct PrimaryButton: View {
    let title: String
    let action: () -> Void
    var isDisabled: Bool = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.onPrimary)
                .frame(maxWidth: .infinity)
                .frame(height: AppSpacing.controlHeight)
                .background(AppColors.primary)
                .clipShape(RoundedRectangle(cornerRadius: AppRadii.large, style: .continuous))
        }
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.5 : 1)
        .accessibilityLabel(title)
    }
}

#Preview {
    PrimaryButton(title: "Start Sketch") {}
        .padding()
        .background(AppColors.background)
}
