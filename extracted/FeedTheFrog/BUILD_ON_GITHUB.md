# Build the APK with GitHub Actions

This project includes `.github/workflows/build-apk.yml`.

The workflow runs on an internet-connected Linux builder, installs Android API 37 and the newest available Android Build-Tools 37.x.x, uses Java 21 and Gradle 9.7.1, builds the debug APK, verifies it exists, and uploads it as a downloadable GitHub Actions artifact.

## Run it
1. Create a GitHub repository.
2. Put the contents of this `FeedTheFrog` folder at the repository root.
3. Push the files to the `main` or `master` branch.
4. Open the repository's **Actions** tab.
5. Select **Build Feed the Frog APK**.
6. Run the workflow manually, or let it run automatically after a push.
7. When the job finishes, download the artifact named `FeedTheFrog-v0.7.2-debug-apk`.
8. Inside that artifact is `app-debug.apk`.

## APK output inside the build
`app/build/outputs/apk/debug/app-debug.apk`

## Notes
- This is a debug APK for testing on an Android device.
- Android may ask you to allow installation from the browser/file-manager app you use to open the APK.
- A Play Store release will later use a signed release AAB/APK instead of the debug APK.
