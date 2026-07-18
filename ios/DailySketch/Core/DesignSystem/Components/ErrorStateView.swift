import SwiftUI

struct ErrorStateView: View {
    let title: String
    let message: String
    var retryTitle: String = "Retry"
    var onRetry: (() -> Void)?

    var body: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 32))
                .foregroundStyle(AppColors.danger)
                .accessibilityHidden(true)

            Text(title)
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)
                .multilineTextAlignment(.center)

            Text(message)
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
                .multilineTextAlignment(.center)

            if let onRetry {
                SecondaryButton(title: retryTitle, action: onRetry)
            }
        }
        .padding(AppSpacing.cardPadding)
        .frame(maxWidth: .infinity)
        .background(AppColors.dangerSoft.opacity(0.35))
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.card, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(title). \(message)")
    }
}

#Preview("Light") {
    ErrorStateView(
        title: "Couldn’t load community sketches",
        message: "Check your connection and try again.",
        onRetry: {}
    )
    .padding()
    .background(AppColors.background)
    .preferredColorScheme(.light)
}

#Preview("Dark") {
    ErrorStateView(
        title: "Couldn’t load community sketches",
        message: "Check your connection and try again.",
        onRetry: {}
    )
    .padding()
    .background(AppColors.background)
    .preferredColorScheme(.dark)
}
