import Foundation
import Observation
@preconcurrency import DailySketchAPI

@MainActor
@Observable
final class AuthSessionStore {
    private(set) var state: AuthState = .guest
    private(set) var currentUser: CurrentUserProfile?

    private let authService: any AuthServing
    private let meFetcher: any MeFetching
    private let profileUpdater: (any ProfileUpdating)?

    init(
        authService: any AuthServing,
        meFetcher: any MeFetching,
        profileUpdater: (any ProfileUpdating)? = nil
    ) {
        self.authService = authService
        self.meFetcher = meFetcher
        self.profileUpdater = profileUpdater
    }

    var isAuthenticated: Bool {
        if case .authenticated = state { return true }
        return false
    }

    var needsProfileCompletion: Bool {
        isAuthenticated && currentUser?.profileCompleted == false
    }

    /// Publish-gated flows must call this before starting upload/publication.
    func requireCompleteProfileForPublishing() -> Bool {
        if needsProfileCompletion {
            return false
        }
        return isAuthenticated
    }

    var accessToken: String? {
        if case .authenticated(let session) = state {
            return session.accessToken
        }
        return nil
    }

    var usesMockAuthentication: Bool {
        authService.usesMockAuthentication
    }

    func bootstrap() async {
        guard let session = await authService.restoreSession() else {
            state = .guest
            currentUser = nil
            return
        }
        await applyAuthenticated(session: session)
    }

    func signUp(displayName: String) async {
        await authenticate {
            try await authService.signUp(displayName: displayName)
        }
    }

    func signIn(displayName: String) async {
        await authenticate {
            try await authService.signIn(displayName: displayName)
        }
    }

    func applyExternalSession(_ session: AuthSession) async {
        await applyAuthenticated(session: session)
    }

    func completeProfile(username: String, displayName: String) async throws {
        guard let token = accessToken else {
            throw ProfileAPIError.sessionExpired
        }
        guard let profileUpdater else {
            throw ProfileAPIError.underlying("Profile updates are unavailable.")
        }
        let profile = try await profileUpdater.updateMe(
            accessToken: token,
            username: username,
            displayName: displayName,
            bio: nil,
            avatarUploadId: nil
        )
        currentUser = profile
    }

    func refreshCurrentUser() async {
        guard let token = accessToken else { return }
        do {
            currentUser = try await meFetcher.fetchMe(accessToken: token)
        } catch {
            // Keep existing profile snapshot on refresh failure.
        }
    }

    func signOut() async {
        await authService.signOut()
        currentUser = nil
        state = .guest
        DailySketchAPITokenBridge.clear()
    }

    func handleExpiredSession() async {
        await authService.signOut()
        currentUser = nil
        DailySketchAPITokenBridge.clear()
        state = .failed(message: AuthServiceError.sessionExpired.localizedDescription)
    }

    private func authenticate(perform: () async throws -> AuthSession) async {
        state = .authenticating
        do {
            let session = try await perform()
            await applyAuthenticated(session: session)
        } catch {
            let message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            state = .failed(message: message)
        }
    }

    private func applyAuthenticated(session: AuthSession) async {
        state = .authenticating
        do {
            let refreshed = try await authService.refreshIfNeeded(session)
            let profile = try await meFetcher.fetchMe(accessToken: refreshed.accessToken)
            currentUser = profile
            state = .authenticated(session: refreshed)
        } catch {
            await authService.signOut()
            currentUser = nil
            DailySketchAPITokenBridge.clear()
            if let authError = error as? AuthServiceError, authError == .sessionExpired {
                state = .failed(message: AuthServiceError.sessionExpired.localizedDescription)
            } else if let profileError = error as? ProfileAPIError, profileError == .sessionExpired {
                state = .failed(message: AuthServiceError.sessionExpired.localizedDescription)
            } else {
                let message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
                state = .failed(message: message)
            }
        }
    }
}

enum DailySketchAPITokenBridge {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var _token: String?

    static func setBearerToken(_ token: String) {
        lock.lock()
        _token = token
        lock.unlock()
    }

    static func clear() {
        lock.lock()
        _token = nil
        lock.unlock()
        DailySketchAPIAPI.customHeaders.removeValue(forKey: "Authorization")
    }

    static var currentToken: String? {
        lock.lock()
        defer { lock.unlock() }
        return _token
    }
}
