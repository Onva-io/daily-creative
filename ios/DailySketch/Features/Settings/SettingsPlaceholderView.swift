import SwiftUI

struct SettingsPlaceholderView: View {
    var body: some View {
        List {
            Section("Sketch Preferences") {
                Text("Timer preference arrives in a later phase.")
                    .foregroundStyle(AppColors.textSecondary)
            }
            Section("Appearance") {
                Text("System / Light / Dark")
                    .foregroundStyle(AppColors.textSecondary)
            }
            Section("About") {
                LabeledContent("Version", value: "0.1.0")
            }
        }
        .scrollContentBackground(.hidden)
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle("Settings")
    }
}

#Preview {
    NavigationStack {
        SettingsPlaceholderView()
    }
}
