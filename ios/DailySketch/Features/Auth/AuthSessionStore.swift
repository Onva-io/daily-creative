import Foundation
import Observation
@preconcurrency import DailyCreativeAPI

@MainActor
@Observable
final class AuthSessionStore {
    private(set) var state: AuthState = .guest
    private(set) var currentUser: CurrentUserProfile?

    private let authService: any AuthServing
    private let meFetcher: any MeFetching
    private let profileUpdater: (any ProfileUpdating)?
    private let policyService: (any PolicyServing)?

    init(
        authService: any AuthServing,
        meFetcher: any MeFetching,
        profileUpdater: (any ProfileUpdating)? = nil,
        policyService: (any PolicyServing)? = nil
    ) {
        self.authService = authService
        self.meFetcher = meFetcher
        self.profileUpdater = profileUpdater
        self.policyService = policyService ?? (meFetcher as? any PolicyServing)
    }

    var isAuthenticated: Bool {
        if case .authenticated = state { return true }
        return false
    }

    var needsProfileCompletion: Bool {
        isAuthenticated && currentUser?.profileCompleted == false && !needsConsent
    }

    var needsConsent: Bool {
        guard isAuthenticated else { return false }
        return currentUser?.consent?.consentRequired == true
    }

    /// Publish-gated flows must call this before starting upload/publication.
    func requireCompleteProfileForPublishing() -> Bool {
        if needsConsent || needsProfileCompletion {
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

    /// Refreshes the session JWT when needed and returns a usable access token.
    /// Returns `nil` (and clears auth) when the refresh token itself has expired.
    func validAccessToken() async -> String? {
        guard case .authenticated(let session) = state else { return nil }
        do {
            let refreshed = try await authService.refreshIfNeeded(session)
            if refreshed.accessToken != session.accessToken {
                state = .authenticated(session: refreshed)
                DailyCreativeAPITokenBridge.setBearerToken(refreshed.accessToken)
            }
            return refreshed.accessToken
        } catch let error as AuthServiceError where error == .sessionExpired {
            await handleExpiredSession()
            return nil
        } catch {
            return session.accessToken
        }
    }

    /// Quietly refreshes an authenticated session (e.g. when returning to the foreground).
    func refreshSessionIfNeeded() async {
        _ = await validAccessToken()
        await refreshCurrentUser()
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

    /// Sends an email OTP without changing auth state to authenticated.
    func sendEmailOTP(email: String) async throws {
        try await authService.sendEmailOTP(email: email)
    }

    func verifyEmailOTP(email: String, code: String) async {
        await authenticate {
            try await authService.verifyEmailOTP(email: email, code: code)
        }
    }

    func signInWithApple() async {
        state = .authenticating
        do {
            let session = try await authService.signInWithApple()
            await applyAuthenticated(session: session)
        } catch AuthServiceError.cancelled {
            state = .guest
        } catch {
            let message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            state = .failed(message: message)
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

    func setDateOfBirth(_ date: Date) async throws {
        guard let token = accessToken else {
            throw ProfileAPIError.sessionExpired
        }
        guard let policyService else {
            throw ProfileAPIError.underlying("Age verification is unavailable.")
        }
        currentUser = try await policyService.setDateOfBirth(accessToken: token, dateOfBirth: date)
    }

    func acceptOutstandingPolicies() async throws {
        guard let token = accessToken else {
            throw ProfileAPIError.sessionExpired
        }
        guard let policyService else {
            throw ProfileAPIError.underlying("Policy acceptance is unavailable.")
        }
        let documents = currentUser?.consent?.currentDocuments ?? []
        let outstanding = Set(currentUser?.consent?.outstandingKinds ?? [])
        let toAccept = documents
            .filter { outstanding.contains($0.kind) }
            .map { (kind: $0.kind, version: $0.version) }
        guard !toAccept.isEmpty else { return }
        let appVersion = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
        try await policyService.acceptPolicies(
            accessToken: token,
            documents: toAccept,
            appVersion: appVersion,
            platform: "ios",
            locale: Locale.current.identifier
        )
        await refreshCurrentUser()
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
        DailyCreativeAPITokenBridge.clear()
    }

    func handleExpiredSession() async {
        await authService.signOut()
        currentUser = nil
        DailyCreativeAPITokenBridge.clear()
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
            if let guestDOB = GuestAgeGateStore.shared.declaredDateOfBirth,
               profile.dateOfBirthSet == false {
                try? await setDateOfBirth(guestDOB)
            }
        } catch {
            await authService.signOut()
            currentUser = nil
            DailyCreativeAPITokenBridge.clear()
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

enum DailyCreativeAPITokenBridge {
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
        DailyCreativeAPIAPI.customHeaders.removeValue(forKey: "Authorization")
    }

    static var currentToken: String? {
        lock.lock()
        defer { lock.unlock() }
        return _token
    }
}
