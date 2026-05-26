# Debug Camera Functionality

The camera is not working because the plugin manager is looking for a different metadata type (`MulticamPluginsCollection`) than what the plugins provide (`WebcamoidPluginsCollection`). This rebranding inconsistency prevents any plugins (camera sources, effects, etc.) from being loaded.

## Proposed Changes

### libAvKys

#### [MODIFY] [akpluginmanager.cpp](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/libAvKys/Lib/src/akpluginmanager.cpp)
- Update `scanPlugins` to accept both `MulticamPluginsCollection` and `WebcamoidPluginsCollection` as valid plugin collection types in [scanPlugins](file:///c:/Users/markk/OneDrive/Desktop/CODE/webcamoid/libAvKys/Lib/src/akpluginmanager.cpp#L338).

## Rebuild and Redeploy
Since the binary in `multicam-data` is not updated automatically, the application must be rebuilt and redeployed.

### Build Steps
1. Re-run CMake configuration for the build directory.
2. Build and install the `multicam` executable and `libAvKys` library.
3. Deploy dependencies using `windeployqt`.

## Verification Plan
1. Restart the application: `.\multicam-data\bin\multicam.exe`.
2. Verify that the camera plugins are found and available in the UI.
