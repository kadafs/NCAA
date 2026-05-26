# Rebranding Webcamoid to Multicam <!-- id: 0 -->

## Status <!-- id: 1 -->
- [x] Planning <!-- id: 2 -->
    - [x] Research existing branding strings <!-- id: 3 -->
    - [x] Create implementation plan <!-- id: 4 -->
- [x] Implementation <!-- id: 5 -->
    - [x] Project-wide string replacement (Webcamoid -> Multicam) <!-- id: 6 -->
    - [x] Standardize resource prefixes (qrc:/multicam/) <!-- id: 7 -->
    - [x] Rename directories and files <!-- id: 8 -->
    - [x] Fix case-sensitive QML property and signal issues <!-- id: 16 -->
    - [x] Update build scripts <!-- id: 9 -->
- [x] Verification <!-- id: 10 -->
    - [x] Run build and install <!-- id: 11 -->
    - [x] Verify executable name and UI strings <!-- id: 12 -->
    - [x] Debug startup failure: fix hardcoded QML resource paths and property names <!-- id: 14 -->
    - [x] Final launch and UI branding check <!-- id: 15 -->
- [ ] Push changes to GitHub <!-- id: 13 -->

## Notes <!-- id: 17 -->
- Critical fix: QML property names must start with lowercase (e.g., `multicamStatus`).
- Critical fix: QML signal handlers follow `onPropertyNameChanged` convention (e.g., `onMulticamLatestVersionChanged`).
- Standardized resource prefix is lowercase `/multicam` to avoid duplication.
