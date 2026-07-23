import DescopeKit
import Foundation

/// Descope-backed authentication used when a real project ID is configured.
///
/// Uses native Email OTP and Sign in with Apple (no Descope Flows / webview).
///
/// Console setup required:
/// - Enable Email OTP in the Descope project and configure OTP email templates.
/// - Enable the Apple social provider; set Client ID to each app’s Bundle Identifier.
/// - In Apple Developer, enable the Sign in with Apple capability on both App IDs.
@MainActor
final class DescopeAuthService: AuthServing {
    private let projectID: String

    init(projectID: String) {
        self.projectID = projectID
        Descope.setup(projectId: projectID)
    }

    var usesMockAuthentication: Bool { false }

    func restoreSession() async -> AuthSession? {
        guard let session = Descope.sessionManager.session, !session.refreshToken.isExpired else {
            return nil
        }
        return makeAuthSession(from: session)
    }

    func signUp(displayName: String) async throws -> AuthSession {
        throw AuthServiceError.notConfigured
    }

    func signIn(displayName: String) async throws -> AuthSession {
        throw AuthServiceError.notConfigured
    }

    func sendEmailOTP(email: String) async throws {
        let loginId = normalizedEmail(email)
        do {
            _ = try await Descope.otp.signUpOrIn(with: .email, loginId: loginId, options: [])
        } catch {
            throw mapDescopeError(error)
        }
    }

    func verifyEmailOTP(email: String, code: String) async throws -> AuthSession {
        let loginId = normalizedEmail(email)
        do {
            let response = try await Descope.otp.verify(with: .email, loginId: loginId, code: code.trimmingCharacters(in: .whitespacesAndNewlines))
            return complete(from: response)
        } catch {
            throw mapDescopeError(error)
        }
    }

    func signInWithApple() async throws -> AuthSession {
        do {
            let response = try await Descope.oauth.native(provider: .apple, options: [])
            return complete(from: response)
        } catch let error as DescopeError where error == .oauthNativeCancelled {
            throw AuthServiceError.cancelled
        } catch {
            throw mapDescopeError(error)
        }
    }

    func complete(from authResponse: AuthenticationResponse) -> AuthSession {
        let session = DescopeSession(from: authResponse)
        Descope.sessionManager.manageSession(session)
        return makeAuthSession(from: session)
    }

    func signOut() async {
        if let refreshJwt = Descope.sessionManager.session?.refreshJwt {
            try? await Descope.auth.revokeSessions(.currentSession, refreshJwt: refreshJwt)
        }
        Descope.sessionManager.clearSession()
    }

    func refreshIfNeeded(_ session: AuthSession) async throws -> AuthSession {
        try await Descope.sessionManager.refreshSessionIfNeeded()
        guard let managed = Descope.sessionManager.session else {
            throw AuthServiceError.sessionExpired
        }
        return makeAuthSession(from: managed)
    }

    private func makeAuthSession(from session: DescopeSession) -> AuthSession {
        AuthSession(
            accessToken: session.sessionJwt,
            subject: session.user.userId,
            displayName: session.user.name
        )
    }

    private func normalizedEmail(_ email: String) -> String {
        email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }

    private func mapDescopeError(_ error: Error) -> AuthServiceError {
        if let descope = error as? DescopeError {
            if descope == .oauthNativeCancelled {
                return .cancelled
            }
            return .underlying(descope.errorDescription ?? descope.localizedDescription)
        }
        return .underlying(error.localizedDescription)
    }
}
