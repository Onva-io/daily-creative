import SwiftUI
import UserNotifications

@main
struct DailyStoryApp: App {
    @State private var dependencies = AppDependencies.live
    @Environment(\.scenePhase) private var scenePhase

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
                .onChange(of: scenePhase) { _, phase in
                    guard phase == .active else { return }
                    Task { await dependencies.auth.refreshSessionIfNeeded() }
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
