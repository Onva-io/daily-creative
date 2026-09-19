import MapKit
import SwiftUI

/// Location editor shown under the caption on the review screen.
///
/// Search, a tappable map to move the pin, a place title, and the per-post
/// choice of whether the pin itself is published.
struct PhotoLocationEditorView: View {
    @Bindable var model: PhotoLocationEditorModel
    let isDisabled: Bool

    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var showsMapWithoutPin = false

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            header

            Text("Optional. Where did you take this?")
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textTertiary)

            if model.isSeeding {
                HStack(spacing: AppSpacing.sm) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Finding your location…")
                        .font(AppTypography.caption)
                        .foregroundStyle(AppColors.textSecondary)
                }
                .accessibilityElement(children: .combine)
            }

            searchField

            if !model.searchResults.isEmpty {
                searchResults
            }

            if let message = model.searchErrorMessage {
                Text(message)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textSecondary)
            }

            if model.hasCoordinates || showsMapWithoutPin {
                map
                Text("Tap the map to move the pin.")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
            } else {
                TertiaryTextButton(
                    title: "Drop a pin on the map",
                    action: { showsMapWithoutPin = true },
                    isDisabled: isDisabled
                )
            }

            if let sourceDescription = model.sourceDescription {
                Text(sourceDescription)
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
            }

            labelField

            Toggle(isOn: $model.shareExact) {
                Text("Share exact location")
                    .font(AppTypography.body)
                    .foregroundStyle(model.hasCoordinates ? AppColors.textPrimary : AppColors.textTertiary)
            }
            .tint(AppColors.primary)
            .disabled(isDisabled || !model.hasCoordinates)
            .accessibilityHint(
                model.hasCoordinates
                    ? "When on, other people see the pin on a map. When off, they only see your place title."
                    : "Add a pin or search for a place first."
            )

            Text(model.sharingFootnote)
                .font(AppTypography.caption)
                .foregroundStyle(AppColors.textTertiary)
        }
        .onChange(of: model.coordinate, initial: true) { _, coordinate in
            guard let coordinate else { return }
            cameraPosition = .region(region(around: coordinate))
        }
    }

    private var header: some View {
        HStack {
            Text("Location")
                .font(AppTypography.headline)
                .foregroundStyle(AppColors.textPrimary)
            Spacer()
            if model.hasLocation {
                Button("Remove") {
                    model.removeLocation()
                    showsMapWithoutPin = false
                }
                .font(AppTypography.bodySmall)
                .foregroundStyle(AppColors.primary)
                .disabled(isDisabled)
                .accessibilityLabel("Remove location")
            }
        }
    }

    private var searchField: some View {
        HStack(spacing: AppSpacing.sm) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(AppColors.textTertiary)
            TextField("Search for a place", text: $model.searchQuery)
                .textInputAutocapitalization(.words)
                .autocorrectionDisabled()
                .submitLabel(.search)
                .onSubmit {
                    Task { await model.runSearch() }
                }
                .accessibilityLabel("Search for a place")
            if model.isSearching {
                ProgressView()
                    .controlSize(.small)
            } else if !model.searchQuery.isEmpty {
                Button {
                    Task { await model.runSearch() }
                } label: {
                    Image(systemName: "arrow.right.circle.fill")
                        .foregroundStyle(AppColors.primary)
                }
                .accessibilityLabel("Search")
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.surfaceTertiary)
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
        .disabled(isDisabled)
    }

    private var searchResults: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(model.searchResults) { result in
                Button {
                    model.select(result)
                } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(result.name)
                            .font(AppTypography.body)
                            .foregroundStyle(AppColors.textPrimary)
                        if let detail = result.detail {
                            Text(detail)
                                .font(AppTypography.caption)
                                .foregroundStyle(AppColors.textSecondary)
                                .lineLimit(1)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, AppSpacing.sm)
                    .padding(.horizontal, AppSpacing.md)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(result.detail.map { "\(result.name), \($0)" } ?? result.name)
                .accessibilityHint("Use this place")
                if result.id != model.searchResults.last?.id {
                    Divider()
                }
            }
        }
        .background(AppColors.surfaceSecondary)
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
        .disabled(isDisabled)
    }

    private var map: some View {
        MapReader { proxy in
            Map(position: $cameraPosition, interactionModes: [.pan, .zoom]) {
                if let coordinate = model.coordinate {
                    Marker(
                        model.label.isEmpty ? "Your photo" : model.label,
                        systemImage: "camera.fill",
                        coordinate: CLLocationCoordinate2D(
                            latitude: coordinate.latitude,
                            longitude: coordinate.longitude
                        )
                    )
                    .tint(AppColors.primary)
                }
            }
            .mapStyle(.standard(pointsOfInterest: .excludingAll))
            .onTapGesture { point in
                guard !isDisabled, let tapped = proxy.convert(point, from: .local) else { return }
                model.movePin(to: GeoCoordinate(latitude: tapped.latitude, longitude: tapped.longitude))
            }
        }
        .frame(height: 220)
        .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
        .accessibilityLabel(
            model.hasCoordinates ? "Map with a pin where your photo was taken" : "Map. Tap to drop a pin."
        )
    }

    private var labelField: some View {
        VStack(alignment: .leading, spacing: AppSpacing.xs) {
            TextField("Place title, e.g. Brighton seafront", text: $model.label)
                .textInputAutocapitalization(.words)
                .padding(AppSpacing.md)
                .background(AppColors.surfaceTertiary)
                .clipShape(RoundedRectangle(cornerRadius: AppRadii.medium, style: .continuous))
                .accessibilityLabel("Place title")
                .disabled(isDisabled)

            if model.label.count >= PhotoLocationLimits.maxLabelLength - 20 {
                Text("\(model.label.count)/\(PhotoLocationLimits.maxLabelLength)")
                    .font(AppTypography.caption)
                    .foregroundStyle(AppColors.textTertiary)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }

    private func region(around coordinate: GeoCoordinate) -> MKCoordinateRegion {
        MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: coordinate.latitude, longitude: coordinate.longitude),
            span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
        )
    }
}

#Preview("Seeded from photo") {
    let draft = try! JSONEncoder().encode(
        PhotoLocationDraft(
            coordinate: GeoCoordinate(latitude: 50.8198, longitude: -0.1372),
            label: "Brighton seafront",
            source: .exif,
            shareExact: false
        )
    )
    ScrollView {
        PhotoLocationEditorView(
            model: PhotoLocationEditorModel(
                draft: LocalDraft(
                    id: UUID(),
                    localSessionId: UUID(),
                    serverSessionId: nil,
                    promptId: UUID(),
                    promptWords: ["Salt", "Light", "Iron"],
                    promptAccessibilityLabel: "Today’s prompt: Salt, Light, Iron.",
                    promptDate: Date(),
                    timerMode: "no_timer",
                    selectedTimerSeconds: nil,
                    sessionStartedAt: Date(),
                    imageFileName: "preview.jpg",
                    caption: nil,
                    createdAt: Date(),
                    updatedAt: Date(),
                    pendingAuthentication: false,
                    pendingPublication: false,
                    contentExtras: draft
                ),
                captured: nil,
                imageLocationReader: FixedImageLocationReader(),
                deviceLocationProvider: FixedDeviceLocationProvider(),
                placeSearcher: FixedPlaceSearcher()
            ),
            isDisabled: false
        )
        .padding()
    }
}

#Preview("Empty") {
    ScrollView {
        PhotoLocationEditorView(
            model: PhotoLocationEditorModel(
                draft: LocalDraft(
                    id: UUID(),
                    localSessionId: UUID(),
                    serverSessionId: nil,
                    promptId: UUID(),
                    promptWords: ["Salt", "Light", "Iron"],
                    promptAccessibilityLabel: "Today’s prompt: Salt, Light, Iron.",
                    promptDate: Date(),
                    timerMode: "no_timer",
                    selectedTimerSeconds: nil,
                    sessionStartedAt: Date(),
                    imageFileName: "preview.jpg",
                    caption: nil,
                    createdAt: Date(),
                    updatedAt: Date(),
                    pendingAuthentication: false,
                    pendingPublication: false
                ),
                captured: nil,
                imageLocationReader: FixedImageLocationReader(),
                deviceLocationProvider: FixedDeviceLocationProvider(),
                placeSearcher: FixedPlaceSearcher()
            ),
            isDisabled: false
        )
        .padding()
    }
    .preferredColorScheme(.dark)
}
