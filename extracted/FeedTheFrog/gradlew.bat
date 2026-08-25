@echo off
set DIR=%~dp0
if not exist "%DIR%gradle\wrapper\gradle-wrapper.jar" (
  echo gradle-wrapper.jar is not bundled in this prototype. Open the project in Android Studio, or install Gradle 9.5 and run: gradle wrapper --gradle-version 9.5.0
  exit /b 1
)
java -classpath "%DIR%gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain %*
