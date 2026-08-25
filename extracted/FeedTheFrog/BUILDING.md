# Building Feed the Frog

## Required local tools
- Java 17 or newer (Java 21 is supported by the supplied Gradle setup).
- Gradle 9.7.1 (the wrapper is configured for 9.7.1).
- Android SDK Platform 37.
- Android SDK Build-Tools and Platform-Tools.
- Internet access for the first Gradle sync so Android Gradle Plugin 9.3.1 and AndroidX/Compose dependencies can be downloaded.

## Android Studio method
1. Open the `FeedTheFrog` folder in Android Studio.
2. Allow Android Studio to install/sync the required SDK components if prompted.
3. Confirm SDK Platform 37 is installed in SDK Manager.
4. Run the `app` configuration, or choose Build > Build APK(s).

## Command-line method
1. Copy `local.properties.example` to `local.properties`.
2. Set `sdk.dir` to your Android SDK directory.
3. Run `build-apk.bat` on Windows or `./build-apk.sh` on macOS/Linux.
4. The debug APK will be written to:
   `app/build/outputs/apk/debug/app-debug.apk`

## Build versions
- Android Gradle Plugin: 9.3.1
- Gradle: 9.7.1
- Kotlin/Compose plugin: 2.3.21
- compileSdk / targetSdk: 37
- minSdk: 26
