@echo off
setlocal
cd /d "%~dp0"
if not exist local.properties (
  if "%ANDROID_HOME%"=="" if "%ANDROID_SDK_ROOT%"=="" (
    echo Android SDK location not configured.
    echo Copy local.properties.example to local.properties and set sdk.dir,
    echo or set ANDROID_HOME / ANDROID_SDK_ROOT.
    exit /b 2
  )
)
call gradlew.bat --no-daemon clean assembleDebug
if errorlevel 1 exit /b %errorlevel%
set APK=%CD%\app\build\outputs\apk\debug\app-debug.apk
if exist "%APK%" (
  echo.
  echo APK created: %APK%
) else (
  echo Build finished but APK was not found at the expected path.
  exit /b 3
)
