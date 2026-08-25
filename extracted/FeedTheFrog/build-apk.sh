#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ ! -f local.properties && -z "$SDK_ROOT" ]]; then
  echo "Android SDK location not configured."
  echo "Copy local.properties.example to local.properties and set sdk.dir,"
  echo "or set ANDROID_HOME / ANDROID_SDK_ROOT."
  exit 2
fi

# GitHub's runner image may not already have API 37 installed. Install the
# exact platform/build-tools this project compiles against when sdkmanager is
# available. This is safe to skip on local machines that already have them.
if command -v sdkmanager >/dev/null 2>&1; then
  yes | sdkmanager --licenses >/dev/null 2>&1 || true
  sdkmanager "platform-tools" >/dev/null

  PLATFORM_PACKAGE="$(sdkmanager --list \
    | awk -F'|' '/platforms;android-37(\.0)?[[:space:]]*\|/ {gsub(/[[:space:]]/, "", $1); print $1; exit}')"

  if [[ -z "$PLATFORM_PACKAGE" ]]; then
    echo "Android API 37 platform package was not found by sdkmanager."
    sdkmanager --list | grep 'platforms;android-37' || true
    exit 1
  fi

  echo "Ensuring $PLATFORM_PACKAGE is installed"
  sdkmanager "$PLATFORM_PACKAGE" >/dev/null

  BUILD_TOOLS="$(sdkmanager --list \
    | awk -F'|' '/build-tools;37\./ {gsub(/[[:space:]]/, "", $1); print $1}' \
    | sort -V \
    | tail -n 1)"

  if [[ -z "$BUILD_TOOLS" ]]; then
    echo "No Android Build-Tools 37.x.x package was found."
    exit 1
  fi

  echo "Ensuring $BUILD_TOOLS is installed"
  sdkmanager "$BUILD_TOOLS" >/dev/null
fi

# IMPORTANT: Always prefer this project's wrapper. The repository-level
# workflow previously put Gradle 8.11.1 on PATH, but AGP 9.3.1 requires
# Gradle 9.5+. The wrapper is pinned to Gradle 9.7.1.
if [[ -f "$ROOT/gradlew" ]]; then
  chmod +x "$ROOT/gradlew"
  GRADLE="$ROOT/gradlew"
elif [[ -x /mnt/data/gradle-9.7.1/bin/gradle ]]; then
  GRADLE=/mnt/data/gradle-9.7.1/bin/gradle
elif command -v gradle >/dev/null 2>&1; then
  GRADLE="$(command -v gradle)"
else
  echo "Gradle was not found and the Gradle wrapper is missing."
  exit 4
fi

echo "Using Gradle: $GRADLE"
"$GRADLE" --version | sed -n '1,12p'
"$GRADLE" --no-daemon --stacktrace clean :app:assembleDebug

APK="$ROOT/app/build/outputs/apk/debug/app-debug.apk"
if [[ -f "$APK" ]]; then
  echo
  echo "APK created: $APK"
  ls -lh "$APK"
else
  echo "Build finished but APK was not found at the expected path."
  exit 3
fi
