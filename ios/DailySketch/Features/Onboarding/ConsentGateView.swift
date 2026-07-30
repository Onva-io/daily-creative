import SwiftUI

struct ConsentGateView: View {
    @Environment(AppDependencies.self) private var dependencies
    @State private var dateOfBirth = Calendar.current.date(byAdding: .year, value: -18, to: Date()) ?? Date()
    @State private var hasReadPolicies = false
    @State private var isSubmitting = false
    @State private var errorMessage: String?
    @State private var documents: [PolicyDocumentSummary] = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
                    Text("Before you continue")
                        .font(AppTypography.title2)
                        .foregroundStyle(AppColors.textPrimary)

                    Text(introCopy)
                        .font(AppTypography.body)
                        .foregroundStyle(AppColors.textSecondary)

                    if needsAge {
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text("Date of birth")
                                .font(AppTypography.headline)
                            DatePicker(
                                "Date of birth",
                                selection: $dateOfBirth,
                                in: ...Date(),
                                displayedComponents: .date
                            )
                            .labelsHidden()
                            .accessibilityLabel("Date of birth")
                            Text("You must be at least \(minimumAge) years old.")
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                        }
                    }

                    if !documents.isEmpty {
                        VStack(alignment: .leading, spacing: AppSpacing.md) {
                            ForEach(documents) { document in
                                DisclosureGroup(document.title) {
                                    Text(document.bodyMarkdown)
                                        .font(AppTypography.caption)
                                        .foregroundStyle(AppColors.textSecondary)
                                        .textSelection(.enabled)
                                }
                            }
                        }

                        Toggle(isOn: $hasReadPolicies) {
                            Text("I have read and agree to the Terms, Privacy Policy, and Community Guidelines.")
                                .font(AppTypography.body)
                        }
                        .accessibilityLabel("Agree to policies")
                    }

                    if let errorMessage {
                        Text(errorMessage)
                            .font(AppTypography.caption)
                            .foregroundStyle(AppColors.danger)
                    }

                    PrimaryButton(
                        title: isSubmitting ? "Saving…" : "Continue",
                        action: { Task { await submit() } },
                        isDisabled: !canSubmit || isSubmitting
                    )
                }
                .padding(.horizontal, AppSpacing.screenHorizontal)
                .padding(.vertical, AppSpacing.section)
            }
            .background(AppColors.background.ignoresSafeArea())
            .navigationTitle("Agreements")
            .navigationBarTitleDisplayMode(.inline)
            .interactiveDismissDisabled(true)
            .task { await loadDocuments() }
        }
    }

    private var consent: ConsentSnapshot? {
        dependencies.auth.currentUser?.consent
    }

    private var needsAge: Bool {
        consent?.ageRequired == true || dependencies.auth.currentUser?.dateOfBirthSet == false
    }

    private var minimumAge: Int {
        consent?.minimumAge ?? GuestAgeGateStore.shared.minimumAge
    }

    private var needsPolicies: Bool {
        !(consent?.outstandingKinds.isEmpty ?? true)
    }

    private var canSubmit: Bool {
        if needsPolicies && !hasReadPolicies { return false }
        return true
    }

    private var introCopy: String {
        if needsAge && needsPolicies {
            return "Confirm your age and agree to the latest policies to use community features."
        }
        if needsAge {
            return "Confirm your age to continue."
        }
        return "We've updated our policies. Please review and agree to continue."
    }

    private func loadDocuments() async {
        if let current = consent?.currentDocuments, !current.isEmpty {
            documents = current.filter { kind in
                consent?.outstandingKinds.contains(kind.kind) == true
            }
            if documents.isEmpty {
                documents = current
            }
            GuestAgeGateStore.shared.setMinimumAge(consent?.minimumAge ?? 13)
            return
        }
        do {
            documents = try await dependencies.policyService.fetchCurrentPolicies()
            if let minimum = documents.map(\.minimumAge).max() {
                GuestAgeGateStore.shared.setMinimumAge(minimum)
            }
        } catch {
            documents = []
        }
    }

    private func submit() async {
        errorMessage = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            if needsAge {
                try await dependencies.auth.setDateOfBirth(dateOfBirth)
                try? GuestAgeGateStore.shared.declare(dateOfBirth: dateOfBirth)
            }
            if needsPolicies {
                await AgeAssuranceCoordinator.acknowledgeSignificantChangesIfNeeded(
                    documents: documents.filter(\.isSignificantChange)
                )
                try await dependencies.auth.acceptOutstandingPolicies()
            }
            await dependencies.auth.refreshCurrentUser()
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct GuestAgeGateView: View {
    @Bindable var store: GuestAgeGateStore
    @State private var dateOfBirth: Date?
    @State private var pickerDraft = Calendar.current.date(byAdding: .year, value: -18, to: Date()) ?? Date()
    @State private var isDatePickerPresented = false
    @State private var errorMessage: String?

    private static let dateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .long
        formatter.timeStyle = .none
        return formatter
    }()

    private var calculatedAge: Int? {
        guard let dateOfBirth else { return nil }
        return store.age(dateOfBirth: dateOfBirth)
    }

    private var confirmTitle: String {
        if let calculatedAge {
            return "Confirm I am \(calculatedAge) years old"
        }
        return "Confirm I am … years old"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.contentGapLarge) {
            Text("Confirm your age")
                .font(AppTypography.title3)
                .foregroundStyle(AppColors.textPrimary)
            Text("Community content is visible across ages. Enter your date of birth to browse the community. Today’s prompt stays available either way.")
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)

            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                Text("Date of birth")
                    .font(AppTypography.headline)
                    .foregroundStyle(AppColors.textPrimary)
                Button {
                    if let dateOfBirth {
                        pickerDraft = dateOfBirth
                    }
                    isDatePickerPresented = true
                } label: {
                    HStack {
                        Text(dateOfBirth.map { Self.dateFormatter.string(from: $0) } ?? "Select a date")
                            .font(AppTypography.body)
                            .foregroundStyle(dateOfBirth == nil ? AppColors.textSecondary : AppColors.textPrimary)
                        Spacer()
                        Image(systemName: "calendar")
                            .foregroundStyle(AppColors.textSecondary)
                    }
                    .padding(.horizontal, AppSpacing.md)
                    .padding(.vertical, AppSpacing.sm)
                    .background(AppColors.surfaceTertiary)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Date of birth")
                .accessibilityValue(dateOfBirth.map { Self.dateFormatter.string(from: $0) } ?? "Not selected")
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.danger)
            }
            PrimaryButton(
                title: confirmTitle,
                action: {
                    guard let dateOfBirth else { return }
                    do {
                        try store.declare(dateOfBirth: dateOfBirth)
                        errorMessage = nil
                    } catch {
                        errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
                    }
                },
                isDisabled: dateOfBirth == nil
            )
        }
        .padding(AppSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .sheet(isPresented: $isDatePickerPresented) {
            NavigationStack {
                DatePicker(
                    "Date of birth",
                    selection: $pickerDraft,
                    in: ...Date(),
                    displayedComponents: .date
                )
                .datePickerStyle(.wheel)
                .labelsHidden()
                .frame(maxWidth: .infinity)
                .padding()
                .navigationTitle("Date of birth")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") {
                            isDatePickerPresented = false
                        }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") {
                            dateOfBirth = pickerDraft
                            isDatePickerPresented = false
                        }
                    }
                }
            }
            .presentationDetents([.medium])
        }
    }
}
