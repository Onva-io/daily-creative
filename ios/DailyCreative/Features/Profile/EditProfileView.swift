import PhotosUI
import SwiftUI
import UIKit

struct EditProfileView: View {
    @Environment(AppDependencies.self) private var dependencies
    @Environment(\.dismiss) private var dismiss
    @State private var model: EditProfileViewModel?
    @State private var photoItem: PhotosPickerItem?
    @State private var showsDiscardConfirmation = false

    var body: some View {
        Group {
            if let model {
                formContent(model)
            } else {
                LoadingView(message: "Loading profile…")
            }
        }
        .background(AppColors.background.ignoresSafeArea())
        .navigationTitle("Edit Profile")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Cancel") {
                    if model?.hasUnsavedChanges == true {
                        showsDiscardConfirmation = true
                    } else {
                        dismiss()
                    }
                }
            }
            ToolbarItem(placement: .confirmationAction) {
                Button("Save") {
                    Task {
                        await model?.save()
                        if model?.didSave == true {
                            await dependencies.auth.refreshCurrentUser()
                            dismiss()
                        }
                    }
                }
                .disabled(!(model?.canSave ?? false))
            }
        }
        .confirmationDialog(
            "Discard changes?",
            isPresented: $showsDiscardConfirmation,
            titleVisibility: .visible
        ) {
            Button("Discard Changes", role: .destructive) {
                dismiss()
            }
            Button("Keep Editing", role: .cancel) {}
        } message: {
            Text("You have unsaved profile changes.")
        }
        .task {
            if model == nil {
                let next = EditProfileViewModel(
                    profileFetcher: dependencies.profileRepository,
                    profileUpdater: dependencies.profileUpdater,
                    uploadService: dependencies.uploadRepository,
                    directUploader: dependencies.directUploader,
                    accessTokenProvider: { dependencies.auth.accessToken },
                    usernameProvider: { dependencies.auth.currentUser?.username }
                )
                model = next
                await next.load()
            }
        }
        .onChange(of: photoItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let image = UIImage(data: data),
                   let jpeg = image.jpegData(compressionQuality: 0.9)
                {
                    model?.applyPickedImageData(jpeg)
                }
            }
        }
    }

    @ViewBuilder
    private func formContent(_ model: EditProfileViewModel) -> some View {
        Form {
            Section {
                HStack {
                    Spacer()
                    VStack(spacing: AppSpacing.sm) {
                        avatarPreview(model)
                        PhotosPicker(selection: $photoItem, matching: .images) {
                            Text("Change Photo")
                                .font(AppTypography.headline)
                        }
                        .accessibilityLabel("Change Photo")
                        if model.isUploadingAvatar {
                            ProgressView(value: model.uploadProgress)
                                .accessibilityLabel("Uploading avatar")
                        }
                    }
                    Spacer()
                }
                .listRowBackground(Color.clear)
            }

            Section("Profile") {
                TextField("Display name", text: Binding(
                    get: { model.displayName },
                    set: { model.displayName = $0 }
                ))
                TextField("Username", text: Binding(
                    get: { model.username },
                    set: { model.username = $0 }
                ))
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                if let message = model.usernameValidationMessage {
                    Text(message)
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.danger)
                }
                TextField("Bio", text: Binding(
                    get: { model.bio },
                    set: { model.bio = $0 }
                ), axis: .vertical)
                .lineLimit(3...6)
            }

            if let errorMessage = model.errorMessage {
                Section {
                    Text(errorMessage)
                        .font(AppTypography.bodySmall)
                        .foregroundStyle(AppColors.danger)
                }
            }
        }
        .disabled(model.isSaving)
    }

    @ViewBuilder
    private func avatarPreview(_ model: EditProfileViewModel) -> some View {
        if let data = model.selectedAvatarData, let image = UIImage(data: data) {
            Image(uiImage: image)
                .resizable()
                .scaledToFill()
                .frame(width: 84, height: 84)
                .clipShape(Circle())
                .accessibilityLabel("Selected avatar preview")
        } else {
            AvatarView(
                displayName: model.displayName.isEmpty ? "Sketcher" : model.displayName,
                username: model.username.isEmpty ? "sketcher" : model.username,
                avatarURL: model.avatarURL,
                size: .profile
            )
        }
    }
}
