import SwiftUI

@main
struct DailyStoryApp: App {
    @State private var dependencies = AppDependencies.live(module: StoryModule())

    init() {
        CreativeAppBootstrap.configure(imageCacheDiskPath: "daily-story-cache")
    }

    var body: some Scene {
        WindowGroup {
            CreativeAppRootView(dependencies: dependencies)
        }
    }
}
