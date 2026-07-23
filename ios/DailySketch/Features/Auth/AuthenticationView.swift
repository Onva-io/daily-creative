import SwiftUI

struct AuthenticationView: View {
    @Environment(AppDependencies.self) private var dependencies
    @State private var displayName = ""
    @State private var email = ""
    @State private var otpCode = ""
    @State private var step: DescopeStep = .email
    @State private var isSendingOTP = false
    @State private var otpError: String?

    var mode: Mode = .signUp

    enum Mode: Hashable {
        case signUp
        case signIn
    }

    private enum DescopeStep {
        case email
        case code
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppSpacing.contentGapLarge) {
                Text(ProductConfig.current.brandName)
                    .font(AppTypography.title1)
                    .foregroundStyle(AppColors.textPrimary)

                Text(subtitle)
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .multilineTextAlignment(.center)

                if dependencies.auth.usesMockAuthentication {
                    mockAuthContent
                } else {
                    descopeContent
                }

                if let otpError {
                    ErrorStateView(
                        title: "Couldn’t sign in",
                        message: otpError,
                        onRetry: {
                            self.otpError = nil
                        }
                    )
                }

                if case .failed(let message) = dependencies.auth.state {
                    ErrorStateView(
                        title: "Couldn’t sign in",
                        message: message,
                        onRetry: {
                            Task { await retryAuthentication() }
                        }
                    )
                }

                if isBusy {
                    LoadingView(message: loadingMessage)
                }
            }
            .padding(.horizontal, AppSpacing.screenHorizontal)
            .padding(.vertical, AppSpacing.section)
        }
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle(mode == .signUp ? "Create Account" : "Sign In")
        .navigationBarTitleDisplayMode(.inline)
        .disabled(isBusy)
    }

    private var isBusy: Bool {
        if isSendingOTP { return true }
        if case .authenticating = dependencies.auth.state { return true }
        return false
    }

    private var loadingMessage: String {
        if isSendingOTP {
            return "Sending code…"
        }
        return "Signing in…"
    }

    private var subtitle: String {
        switch (dependencies.auth.usesMockAuthentication, mode, step) {
        case (false, _, .code):
            return "Enter the code we sent to \(email)."
        case (_, .signUp, _):
            return "Create a free account to save sketches, build your history, and join the community."
        case (_, .signIn, _):
            return "Welcome back. Sign in to continue your creative journal."
        }
    }

    @ViewBuilder
    private var mockAuthContent: some View {
        VStack(spacing: AppSpacing.md) {
            TextField("Display name (optional)", text: $displayName)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.words)
                .accessibilityLabel("Display name")

            Text("Local mock authentication is active because DESCOPE_PROJECT_ID is unset.")
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)
                .multilineTextAlignment(.center)

            PrimaryButton(title: mode == .signUp ? "Create Free Account" : "Sign In") {
                Task { await retryAuthentication() }
            }
            .accessibilityLabel(mode == .signUp ? "Create Free Account" : "Sign In")
        }
    }

    @ViewBuilder
    private var descopeContent: some View {
        VStack(spacing: AppSpacing.md) {
            switch step {
            case .email:
                emailStepContent
            case .code:
                codeStepContent
            }
        }
    }

    @ViewBuilder
    private var emailStepContent: some View {
        TextField("Email", text: $email)
            .textFieldStyle(.roundedBorder)
            .textContentType(.emailAddress)
            .keyboardType(.emailAddress)
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .accessibilityLabel("Email")

        PrimaryButton(title: "Continue", action: {
            Task { await sendOTP() }
        }, isDisabled: !isValidEmail)

        authDivider

        SecondaryButton(title: "Continue with Apple", action: {
            Task { await signInWithApple() }
        }, systemImage: "apple.logo")
        .accessibilityLabel("Continue with Apple")
    }

    @ViewBuilder
    private var codeStepContent: some View {
        TextField("6-digit code", text: $otpCode)
            .textFieldStyle(.roundedBorder)
            .textContentType(.oneTimeCode)
            .keyboardType(.numberPad)
            .accessibilityLabel("Verification code")

        PrimaryButton(title: "Verify", action: {
            Task { await verifyOTP() }
        }, isDisabled: !isValidOTPCode)

        TertiaryTextButton(title: "Resend code") {
            Task { await sendOTP() }
        }

        TertiaryTextButton(title: "Use a different email") {
            step = .email
            otpCode = ""
            otpError = nil
        }
    }

    private var authDivider: some View {
        HStack(spacing: AppSpacing.sm) {
            Rectangle()
                .fill(AppColors.textTertiary.opacity(0.35))
                .frame(height: 1)
            Text("or")
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textSecondary)
            Rectangle()
                .fill(AppColors.textTertiary.opacity(0.35))
                .frame(height: 1)
        }
    }

    private var isValidEmail: Bool {
        let trimmed = email.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.contains("@") && trimmed.contains(".")
    }

    private var isValidOTPCode: Bool {
        let digits = otpCode.filter(\.isNumber)
        return digits.count >= 6
    }

    private func sendOTP() async {
        otpError = nil
        isSendingOTP = true
        defer { isSendingOTP = false }
        do {
            try await dependencies.auth.sendEmailOTP(email: email)
            step = .code
            otpCode = ""
        } catch {
            otpError = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func verifyOTP() async {
        otpError = nil
        await dependencies.auth.verifyEmailOTP(email: email, code: otpCode)
        finishAuthenticatedNavigation()
    }

    private func signInWithApple() async {
        otpError = nil
        await dependencies.auth.signInWithApple()
        finishAuthenticatedNavigation()
    }

    private func retryAuthentication() async {
        if dependencies.auth.usesMockAuthentication {
            switch mode {
            case .signUp:
                await dependencies.auth.signUp(displayName: displayName)
            case .signIn:
                await dependencies.auth.signIn(displayName: displayName)
            }
            finishAuthenticatedNavigation()
            return
        }

        otpError = nil
        switch step {
        case .email:
            await sendOTP()
        case .code:
            await verifyOTP()
        }
    }

    private func finishAuthenticatedNavigation() {
        dependencies.navigation.finishAuthenticationFlow(
            isAuthenticated: dependencies.auth.isAuthenticated,
            needsProfileCompletion: dependencies.auth.needsProfileCompletion
        )
    }
}

#Preview {
    NavigationStack {
        AuthenticationView(mode: .signUp)
    }
    .environment(AppDependencies.live)
}
