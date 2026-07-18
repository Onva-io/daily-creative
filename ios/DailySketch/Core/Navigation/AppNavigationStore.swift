import Foundation
import Observation

enum AppRoute: Hashable {
    case settings
}

@Observable
final class AppNavigationStore {
    var homePath: [AppRoute] = []
    var profilePath: [AppRoute] = []
}
