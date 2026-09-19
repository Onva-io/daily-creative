import SwiftUI
import UserNotifications

/// Process-wide setup every app target runs before its first view.
enum CreativeAppBootstrap {
    /// - Parameter imageCacheDiskPath: Per-app `URLCache` directory name so
    ///   two apps installed side by side never share cached media.
    @MainActor
    static func configure(imageCacheDiskPath: String) {
        let memoryCapacity = 32 * 1024 * 1024
        let diskCapacity = 256 * 1024 * 1024
        URLCache.shared = URLCache(
            memoryCapacity: memoryCapacity,
            diskCapacity: diskCapacity,
            diskPath: imageCacheDiskPath
        )
        CrashReportingClient.start()
        GuestAgeGateStore.shared.applyTokenHeader()
    }
}

/// Root view shared by every app target.
///
/// An `App` is reduced to three decisions: which `CreativeModule` it ships,
/// its image cache directory, and nothing else. Auth bootstrap, preference
/// hydration, reminder delegate wiring and time-zone handling live here so no
/// target re-implements them.
struct CreativeAppRootView: View {
    let dependencies: AppDependencies
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
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
