import SwiftUI

struct ProfilePlaceholderView: View {
    @Environment(AppDependencies.self) private var dependencies

    var body: some View {
        ScrollView {
            VStack(spacing: AppSpacing.contentGapLarge) {
                Image(systemName: "person.crop.circle")
                    .font(.system(size: 72))
                    .foregroundStyle(AppColors.primary)
                    .accessibilityHidden(true)

                Text("Keep your creative history")
                    .font(AppTypography.title2)
                    .foregroundStyle(AppColors.textPrimary)
                    .multilineTextAlignment(.center)

                Text("Create a free account to save Submissions, streaks, Likes, and Reflections.")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .multilineTextAlignment(.center)

                PrimaryButton(title: "Create Free Account") {}
                    .disabled(true)

                Button("Sign In") {}
                    .font(AppTypography.headline)
                    .foregroundStyle(AppColors.primary)
                    .frame(minHeight: AppSpacing.minimumTouchTarget)
                    .disabled(true)
            }
            .padding(.horizontal, AppSpacing.screenHorizontal)
            .padding(.vertical, AppSpacing.section)
        }
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle("Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    dependencies.navigation.profilePath.append(.settings)
                } label: {
                    Image(systemName: "gearshape")
                }
                .accessibilityLabel("Settings")
            }
        }
    }
}

#Preview {
    NavigationStack {
        ProfilePlaceholderView()
    }
    .environment(AppDependencies.live)
}
