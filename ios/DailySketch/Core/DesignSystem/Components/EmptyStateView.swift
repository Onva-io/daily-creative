import SwiftUI

struct EmptyStateView: View {
    let title: String
    let message: String
    var systemImage: String = "square.and.pencil"
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: systemImage)
                .font(.system(size: 36))
                .foregroundStyle(AppColors.primary)
                .accessibilityHidden(true)

            Text(title)
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)
                .multilineTextAlignment(.center)

            Text(message)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
                .multilineTextAlignment(.center)

            if let actionTitle, let action {
                PrimaryButton(title: actionTitle, action: action)
            }
        }
        .padding(AppSpacing.cardPadding)
        .frame(maxWidth: .infinity)
        .background(AppColors.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(title). \(message)")
    }
}

#Preview("Light") {
    EmptyStateView(
        title: "No sketches yet",
        message: "Be the first to share an interpretation of today’s prompt."
    )
    .padding()
    .background(AppColors.background)
    .preferredColorScheme(.light)
}

#Preview("Dark") {
    EmptyStateView(
        title: "No sketches yet",
        message: "Be the first to share an interpretation of today’s prompt."
    )
    .padding()
    .background(AppColors.background)
    .preferredColorScheme(.dark)
}
