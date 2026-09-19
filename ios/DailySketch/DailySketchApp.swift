import SwiftUI

@main
struct DailySketchApp: App {
    @State private var dependencies = AppDependencies.live(module: SketchModule())

    init() {
        CreativeAppBootstrap.configure(imageCacheDiskPath: "daily-sketch-image-cache")
    }

    var body: some Scene {
        WindowGroup {
            CreativeAppRootView(dependencies: dependencies)
        }
    }
}
