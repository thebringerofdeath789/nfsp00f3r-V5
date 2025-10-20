#!/usr/bin/env bash
set -euo pipefail

# Generate the Gradle wrapper for the Android app on POSIX systems (Linux/macOS).
# Usage:
#   bash android-app/scripts/generate-gradle-wrapper.sh [--force]
#
# Behavior:
#  - If the wrapper JAR already exists and --force is not provided, the script
#    exits successfully.
#  - If 'gradle' is available in PATH the script runs 'gradle wrapper'.
#  - If 'gradle' is missing and 'apt-get' is present the script will attempt to
#    install Gradle via apt-get (requires sudo) and then run 'gradle wrapper'.
#  - If automatic generation fails the script exits non-zero and prints a
#    short remediation message.

FORCE=0
if [ "${1-}" = "--force" ]; then
  FORCE=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
WRAPPER_JAR="$PROJECT_DIR/gradle/wrapper/gradle-wrapper.jar"

if [ -f "$WRAPPER_JAR" ] && [ "$FORCE" -eq 0 ]; then
  echo "Gradle wrapper already present: $WRAPPER_JAR"
  exit 0
fi

if command -v gradle >/dev/null 2>&1; then
  echo "Gradle found in PATH; generating wrapper..."
  (cd "$PROJECT_DIR" && gradle wrapper)
  if [ -f "$WRAPPER_JAR" ]; then
    echo "Gradle wrapper generated successfully: $WRAPPER_JAR"
    exit 0
  else
    echo "Failed to generate Gradle wrapper using installed gradle"
    exit 2
  fi
fi

if command -v apt-get >/dev/null 2>&1; then
  echo "No 'gradle' command found. Attempting to install Gradle via apt-get (requires sudo)..."
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y || true
    sudo apt-get install -y gradle || true
  else
    apt-get update -y || true
    apt-get install -y gradle || true
  fi

  if command -v gradle >/dev/null 2>&1; then
    (cd "$PROJECT_DIR" && gradle wrapper)
    if [ -f "$WRAPPER_JAR" ]; then
      echo "Gradle wrapper generated successfully after apt install: $WRAPPER_JAR"
      exit 0
    fi
  fi
fi

echo "Gradle not found and automatic installation failed."
echo "Please install Gradle (https://gradle.org/install/), open the project in Android Studio and generate a wrapper, or run: gradle wrapper --gradle-version 8.5"
exit 1
