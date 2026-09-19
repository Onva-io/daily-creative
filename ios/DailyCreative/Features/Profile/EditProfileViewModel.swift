import Foundation
import Observation

@MainActor
@Observable
final class EditProfileViewModel {
    var displayName: String = ""
    var username: String = ""
    var bio: String = ""
    var avatarURL: URL?
    private(set) var selectedAvatarData: Data?
    private(set) var isSaving = false
    private(set) var isUploadingAvatar = false
    private(set) var uploadProgress: Double = 0
    private(set) var errorMessage: String?
    private(set) var didSave = false

    private var initialDisplayName = ""
    private var initialUsername = ""
    private var initialBio = ""
    private var initialAvatarURL: URL?

    private let profileFetcher: any ProfileFetching
    private let profileUpdater: any ProfileUpdating
    private let uploadService: any UploadServing
    private let directUploader: any DirectUploadTransporting
    private let accessTokenProvider: () -> String?
    private let usernameProvider: () -> String?

    init(
        profileFetcher: any ProfileFetching,
        profileUpdater: any ProfileUpdating,
        uploadService: any UploadServing,
        directUploader: any DirectUploadTransporting,
        accessTokenProvider: @escaping () -> String?,
        usernameProvider: @escaping () -> String?
    ) {
        self.profileFetcher = profileFetcher
        self.profileUpdater = profileUpdater
        self.uploadService = uploadService
        self.directUploader = directUploader
        self.accessTokenProvider = accessTokenProvider
        self.usernameProvider = usernameProvider
    }

    var hasUnsavedChanges: Bool {
        displayName != initialDisplayName
            || username != initialUsername
            || bio != initialBio
            || selectedAvatarData != nil
    }

    var usernameValidationMessage: String? {
        UsernameValidator.validationMessage(for: username)
    }

    var canSave: Bool {
        !isSaving
            && !isUploadingAvatar
            && UsernameValidator.isValidFormat(username)
            && !displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && hasUnsavedChanges
    }

    func load() async {
        guard let usernameValue = usernameProvider() else {
            errorMessage = "Complete your profile before editing."
            return
        }
        do {
            let profile = try await profileFetcher.fetchPublicProfile(
                username: usernameValue,
                accessToken: accessTokenProvider(),
                creativeType: ProductConfig.current.creativeTypeID
            )
            seed(from: profile)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func seed(from profile: PublicProfileModel) {
        displayName = profile.displayName
        username = profile.username
        bio = profile.bio ?? ""
        avatarURL = profile.avatarURL
        initialDisplayName = profile.displayName
        initialUsername = profile.username
        initialBio = profile.bio ?? ""
        initialAvatarURL = profile.avatarURL
        selectedAvatarData = nil
        didSave = false
        errorMessage = nil
    }

    func applyPickedImageData(_ data: Data?) {
        selectedAvatarData = data
    }

    func save() async {
        guard canSave else { return }
        guard let token = accessTokenProvider() else {
            errorMessage = ProfileAPIError.sessionExpired.localizedDescription
            return
        }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        do {
            var avatarUploadId: UUID?
            if let selectedAvatarData {
                avatarUploadId = try await uploadAvatar(data: selectedAvatarData, accessToken: token)
            }

            let trimmedDisplay = displayName.trimmingCharacters(in: .whitespacesAndNewlines)
            let trimmedUsername = username.trimmingCharacters(in: .whitespacesAndNewlines)
            let trimmedBio = bio.trimmingCharacters(in: .whitespacesAndNewlines)
            let bioValue: String? = trimmedBio.isEmpty ? nil : trimmedBio

            let updated = try await profileUpdater.updateMe(
                accessToken: token,
                username: trimmedUsername,
                displayName: trimmedDisplay,
                bio: bioValue,
                avatarUploadId: avatarUploadId
            )
            avatarURL = updated.avatarURL
            initialDisplayName = trimmedDisplay
            initialUsername = trimmedUsername
            initialBio = bioValue ?? ""
            initialAvatarURL = updated.avatarURL
            selectedAvatarData = nil
            didSave = true
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func uploadAvatar(data: Data, accessToken: String) async throws -> UUID {
        isUploadingAvatar = true
        uploadProgress = 0
        defer {
            isUploadingAvatar = false
            uploadProgress = 0
        }

        let slot = try await uploadService.createUpload(
            accessToken: accessToken,
            contentType: "image/jpeg",
            byteSize: data.count,
            purpose: .avatar,
            idempotencyKey: "avatar-\(UUID().uuidString)"
        )
        guard let uploadURL = slot.signedUploadURL, let method = slot.signedUploadMethod else {
            throw ProfileAPIError.underlying("Avatar upload could not be prepared.")
        }
        try await directUploader.upload(
            data: data,
            to: uploadURL,
            method: method,
            headers: slot.signedUploadHeaders,
            progress: { [weak self] value in
                Task { @MainActor in
                    self?.uploadProgress = value
                }
            }
        )
        let ready = try await uploadService.completeUpload(
            accessToken: accessToken,
            uploadId: slot.id
        )
        return ready.id
    }
}
