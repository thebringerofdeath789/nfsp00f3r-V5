#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
if [ -x "$ROOT_DIR/gradlew" ]; then
  GRADLE_EXEC="$ROOT_DIR/gradlew"
elif [ -x "/usr/bin/gradle" ]; then
  GRADLE_EXEC="/usr/bin/gradle"
elif [ -x "/tmp/gradle-8.6/bin/gradle" ]; then
  GRADLE_EXEC="/tmp/gradle-8.6/bin/gradle"
else
  echo "No gradle executable found. Install Gradle or download gradle-8.6 to /tmp/gradle-8.6." >&2
  exit 1
fi

echo "Using gradle: $GRADLE_EXEC"
JAVA_HOME=${JAVA_HOME:-/opt/openjdk-bin-17}
echo "Using JAVA_HOME: $JAVA_HOME"
"$GRADLE_EXEC" assembleDebug --no-daemon
