import PhotosUI
import SwiftUI
import UIKit

struct CaptureSourceView: View {
    let cameraAuthorizer: any CameraAuthorizing
    let onImageData: (Data) -> Void
    let onCancel: () -> Void
    let onValidationError: (String) -> Void

    @State private var showsCamera = false
    @State private var showsLibraryPicker = false
    @State private var librarySelection: PhotosPickerItem?
    @State private var permissionDeniedMessage: String?
    @State private var isRequestingPermission = false

    private var cameraBlocked: Bool {
        !cameraAuthorizer.isCameraAvailable
            || cameraAuthorizer.status == .denied
            || cameraAuthorizer.status == .restricted
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: AppSpacing.contentGapLarge) {
                Text("Add your sketch")
                    .font(AppTypography.title2)
                    .foregroundStyle(AppColors.textPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("Photograph your drawing or choose an existing photo from your library.")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                if let permissionDeniedMessage {
                    VStack(alignment: .leading, spacing: AppSpacing.sm) {
                        Text(permissionDeniedMessage)
                            .font(AppTypography.bodySmall)
                            .foregroundStyle(AppColors.textSecondary)
                        Button("Open Settings") {
                            if let url = URL(string: UIApplication.openSettingsURLString) {
                                UIApplication.shared.open(url)
                            }
                        }
                        .font(AppTypography.bodySmall)
                        .foregroundStyle(AppColors.primary)
                        .accessibilityLabel("Open Settings")
                    }
                    .padding(AppSpacing.md)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(AppColors.surfaceSecondary)
                    .clipShape(RoundedRectangle(cornerRadius: AppRadii.large, style: .continuous))
                }

                VStack(spacing: AppSpacing.contentGap) {
                    if cameraBlocked {
                        PrimaryButton(
                            title: "Choose from Library",
                            action: { showsLibraryPicker = true },
                            systemImage: "photo.on.rectangle"
                        )
                        SecondaryButton(
                            title: "Take Photo unavailable",
                            action: {
                                permissionDeniedMessage =
                                    "Camera access is unavailable. Choose a photo from your library, or enable Camera in Settings."
                            },
                            isDisabled: true,
                            systemImage: "camera"
                        )
                    } else {
                        PrimaryButton(
                            title: "Take Photo",
                            action: { Task { await takePhotoTapped() } },
                            isDisabled: isRequestingPermission,
                            systemImage: "camera"
                        )
                        SecondaryButton(
                            title: "Choose from Library",
                            action: { showsLibraryPicker = true },
                            systemImage: "photo.on.rectangle"
                        )
                    }

                    TertiaryTextButton(title: "Go Back", action: onCancel)
                }

                Spacer()
            }
            .padding(.horizontal, AppSpacing.screenHorizontal)
            .padding(.vertical, AppSpacing.lg)
            .background(AppColors.background.ignoresSafeArea())
            .navigationTitle("Capture")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { onCancel() }
                }
            }
            .fullScreenCover(isPresented: $showsCamera) {
                CameraPickerView(
                    onImage: { image in
                        showsCamera = false
                        accept(image: image)
                    },
                    onCancel: { showsCamera = false }
                )
                .ignoresSafeArea()
            }
            .photosPicker(
                isPresented: $showsLibraryPicker,
                selection: $librarySelection,
                matching: .images
            )
            .onChange(of: librarySelection) { _, item in
                guard let item else { return }
                Task {
                    await handleLibraryItem(item)
                }
            }
            .onAppear {
                if cameraBlocked, permissionDeniedMessage == nil {
                    permissionDeniedMessage =
                        "Camera access isn’t available. You can still choose a photo from your library."
                }
            }
        }
    }

    private func takePhotoTapped() async {
        isRequestingPermission = true
        defer { isRequestingPermission = false }

        switch cameraAuthorizer.status {
        case .authorized:
            showsCamera = true
        case .notDetermined:
            let granted = await cameraAuthorizer.requestAccess()
            if granted {
                showsCamera = true
            } else {
                permissionDeniedMessage =
                    "Camera access was denied. Choose a photo from your library, or enable Camera in Settings."
            }
        case .denied, .restricted:
            permissionDeniedMessage =
                "Camera access isn’t available. Choose a photo from your library, or enable Camera in Settings."
        }
    }

    private func handleLibraryItem(_ item: PhotosPickerItem) async {
        do {
            guard let data = try await item.loadTransferable(type: Data.self) else {
                // Selection cancelled or transferred nothing — stay on this screen.
                librarySelection = nil
                return
            }
            let image = try ImageValidation.validatedImage(from: data)
            accept(image: image)
        } catch {
            let message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            onValidationError(message)
        }
        librarySelection = nil
    }

    private func accept(image: UIImage) {
        do {
            let data = try ImageValidation.normalizedJPEGData(from: image)
            onImageData(data)
        } catch {
            let message = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            onValidationError(message)
        }
    }
}

#Preview {
    CaptureSourceView(
        cameraAuthorizer: FakeCameraAuthorizer(),
        onImageData: { _ in },
        onCancel: {},
        onValidationError: { _ in }
    )
}

#Preview("Permission Denied") {
    CaptureSourceView(
        cameraAuthorizer: FakeCameraAuthorizer(status: .denied, isCameraAvailable: false),
        onImageData: { _ in },
        onCancel: {},
        onValidationError: { _ in }
    )
}
