import SwiftUI
import UserNotifications

@main
struct DailyStoryApp: App {
    @State private var dependencies = AppDependencies.live

    init() {
        let memoryCapacity = 32 * 1024 * 1024
        let diskCapacity = 256 * 1024 * 1024
        URLCache.shared = URLCache(
            memoryCapacity: memoryCapacity,
            diskCapacity: diskCapacity,
            diskPath: "daily-story-cache"
        )
        CrashReportingClient.start()
    }

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environment(dependencies)
                .preferredColorScheme(dependencies.appearanceStore.colorScheme)
                .task {
                    UNUserNotificationCenter.current().delegate = dependencies.reminderNotificationDelegate
                    dependencies.analytics.track(.appOpened)
                    await dependencies.auth.bootstrap()
                    await dependencies.hydrateUserPreferences()
                }
                .onReceive(NotificationCenter.default.publisher(for: .NSSystemTimeZoneDidChange)) { _ in
                    Task { await dependencies.hydrateUserPreferences() }
                }
                .onReceive(NotificationCenter.default.publisher(for: UIApplication.significantTimeChangeNotification)) { _ in
                    Task { await dependencies.hydrateUserPreferences() }
                }
        }
    }
}
