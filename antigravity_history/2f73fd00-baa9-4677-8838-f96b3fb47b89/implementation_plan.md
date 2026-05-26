# Plan: Rename Project to multicam

Renaming the project involves consistently replacing the name "Webcamoid" with "multicam" across the entire codebase to maintain branding and functionality.

## Proposed Changes

### Build System (CMake)
- **Root [CMakeLists.txt](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/CMakeLists.txt)**:
    - `project(Webcamoid)` -> `project(multicam)`
    - Update `MAIN_EXECUTABLE`, `INSTALLER_ICON`, and `DEB_INSTALL_PREFIX`.
- **[libAvKys/cmake/ProjectCommons.cmake](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/libAvKys/cmake/ProjectCommons.cmake)**: Update project-wide constants and identifiers.
- **[StandAlone/src/CMakeLists.txt](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/StandAlone/src/CMakeLists.txt)**: Update output binary name and resource linked names.

### UI and Source Code
- **[StandAlone/src/main.cpp](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/StandAlone/src/main.cpp)**: Update `QCoreApplication` names and window titles.
- **[StandAlone/share/qml/main.qml](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/StandAlone/share/qml/main.qml)**: Update visible titles in the UI.
- **Resources**:
    - Rename `StandAlone/Webcamoid.qrc` to `StandAlone/multicam.qrc`.
    - Rename `StandAlone/Webcamoid.rc` to `StandAlone/multicam.rc`.
    - Update window icons and associated paths.

### Infrastructure
- **[run_cmake_debug.bat](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/run_cmake_debug.bat)**: Update the executable path from `webcamoid.exe` to `multicam.exe`.
- **GitHub**: Commit with the message "Rename: Webcamoid -> multicam" and push.

## User Review Required

> [!WARNING]
> Renaming the project affects binary names and installation paths. Existing shortcuts or scripts pointing to `webcamoid.exe` will need to be updated to `multicam.exe`.

## Verification Plan

### Automated Tests
- Run `run_cmake_debug.bat` and ensure the build completes.
- Check that `webcamoid-data/bin/multicam.exe` exists.

### Manual Verification
- Launch `multicam.exe` and verify that the window title and branding reflect the new name.

### Automated Tests
- Run `cmake --build build --target install` and verify the output binary name.

### Manual Verification
- Launch `multicam.exe`.
- Verify the window title and "About" dialog display "multicam".
