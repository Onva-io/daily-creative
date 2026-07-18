import Foundation
import Observation

@Observable
final class AppDependencies {
    let environment: AppEnvironment
    let navigation: AppNavigationStore

    init(environment: AppEnvironment, navigation: AppNavigationStore = AppNavigationStore()) {
        self.environment = environment
        self.navigation = navigation
    }

    static var live: AppDependencies {
        AppDependencies(environment: .current)
    }
}
