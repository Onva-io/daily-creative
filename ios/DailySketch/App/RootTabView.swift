import SwiftUI

struct RootTabView: View {
    @Environment(AppDependencies.self) private var dependencies

    var body: some View {
        @Bindable var navigation = dependencies.navigation

        TabView {
            NavigationStack(path: $navigation.homePath) {
                HomePlaceholderView()
                    .navigationDestination(for: AppRoute.self) { route in
                        switch route {
                        case .settings:
                            SettingsPlaceholderView()
                        }
                    }
            }
            .tabItem {
                Label("Home", systemImage: "house")
            }

            NavigationStack(path: $navigation.profilePath) {
                ProfilePlaceholderView()
                    .navigationDestination(for: AppRoute.self) { route in
                        switch route {
                        case .settings:
                            SettingsPlaceholderView()
                        }
                    }
            }
            .tabItem {
                Label("Profile", systemImage: "person")
            }
        }
        .tint(AppColors.primary)
    }
}

#Preview {
    RootTabView()
        .environment(AppDependencies.live)
}
