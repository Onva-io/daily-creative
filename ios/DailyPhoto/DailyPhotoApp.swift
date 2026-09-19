import SwiftUI

@main
struct DailyPhotoApp: App {
    @State private var dependencies = AppDependencies.live(module: PhotoModule())

    init() {
        CreativeAppBootstrap.configure(imageCacheDiskPath: "daily-photo-image-cache")
    }

    var body: some Scene {
        WindowGroup {
            CreativeAppRootView(dependencies: dependencies)
        }
    }
}
