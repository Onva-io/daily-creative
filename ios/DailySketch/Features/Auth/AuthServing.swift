import Foundation

@MainActor
protocol AuthServing: AnyObject {
    var usesMockAuthentication: Bool { get }
    func restoreSession() async -> AuthSession?
    func signUp(displayName: String) async throws -> AuthSession
    func signIn(displayName: String) async throws -> AuthSession
    /// Sends an email OTP for sign-up or sign-in. Does not create a session.
    func sendEmailOTP(email: String) async throws
    /// Verifies an email OTP and returns a managed session on success.
    func verifyEmailOTP(email: String, code: String) async throws -> AuthSession
    /// Presents native Sign in with Apple and returns a managed session on success.
    func signInWithApple() async throws -> AuthSession
    func signOut() async
    func refreshIfNeeded(_ session: AuthSession) async throws -> AuthSession
}

enum AuthServiceError: LocalizedError, Equatable {
    case cancelled
    case notConfigured
    case sessionExpired
    case underlying(String)

    var errorDescription: String? {
        switch self {
        case .cancelled:
            return "Sign-in was cancelled."
        case .notConfigured:
            return "Descope is not configured. Set DESCOPE_PROJECT_ID or use local mock auth."
        case .sessionExpired:
            return "Your session expired. Please sign in again."
        case .underlying(let message):
            return message
        }
    }
}
