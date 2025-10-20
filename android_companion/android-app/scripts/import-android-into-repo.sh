#!/usr/bin/env bash
set -euo pipefail

# import-android-into-repo.sh
# POSIX shell variant of the import helper. Intended to be run from the
# workspace root or by calling the script directly. Use --dry-run to inspect
# proposed changes.

NEW_APP_ID="com.emvresearch.nfsp00f3rV5c"
OLD_APP_ID="com.nf_sp00f.app"
REMOVE_NESTED_GIT=0
PRESERVE_UPSTREAM_GIT=0
COMMIT=0
DRY_RUN=0

usage() {
  cat <<EOF
Usage: $0 [--new-app-id ID] [--remove-nested-git] [--preserve-upstream-git] [--commit] [--dry-run]
  --new-app-id       The applicationId to set in the imported Android app
  --remove-nested-git  Remove android_companion/.git (dangerous without backup)
  --preserve-upstream-git  Move nested .git to docs/backups/android_companion_upstream_git
  --commit           Stage & commit changes in the parent repository
  --dry-run          Print planned actions and exit
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --new-app-id) NEW_APP_ID="$2"; shift 2;;
    --remove-nested-git) REMOVE_NESTED_GIT=1; shift;;
    --preserve-upstream-git) PRESERVE_UPSTREAM_GIT=1; shift;;
    --commit) COMMIT=1; shift;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_COMPANION_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ANDROID_APP_DIR="$ANDROID_COMPANION_DIR/android-app"
APP_SRC_JAVA_DIR="$ANDROID_APP_DIR/app/src/main/java"

OLD_PKG_PATH=${OLD_APP_ID//./\/}
NEW_PKG_PATH=${NEW_APP_ID//./\/}

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN — planned actions:"
  echo " - Replace applicationId '$OLD_APP_ID' -> '$NEW_APP_ID' in app/build.gradle"
  echo " - Replace AndroidManifest package attribute"
  echo " - Replace Kotlin package declarations and move sources from $OLD_PKG_PATH -> $NEW_PKG_PATH"
  if [ "$REMOVE_NESTED_GIT" -eq 1 ]; then echo " - Remove nested .git"; fi
  if [ "$PRESERVE_UPSTREAM_GIT" -eq 1 ]; then echo " - Move nested .git to docs/backups/android_companion_upstream_git"; fi
  if [ "$COMMIT" -eq 1 ]; then echo " - Stage & commit to parent repo"; fi
  exit 0
fi

echo "Importing Android companion into parent repository (workspace: $(pwd))"

# Step 1: nested .git handling
if [ -d "$ANDROID_COMPANION_DIR/.git" ]; then
  if [ "$PRESERVE_UPSTREAM_GIT" -eq 1 ]; then
    BACKUP_DIR="$ANDROID_COMPANION_DIR/../docs/backups/android_companion_upstream_git"
    mkdir -p "$BACKUP_DIR"
    echo "Moving nested .git to $BACKUP_DIR"
    mv "$ANDROID_COMPANION_DIR/.git" "$BACKUP_DIR/"
  elif [ "$REMOVE_NESTED_GIT" -eq 1 ]; then
    echo "Removing nested .git (per --remove-nested-git)"
    rm -rf "$ANDROID_COMPANION_DIR/.git"
  else
    echo "Nested .git detected at $ANDROID_COMPANION_DIR/.git. Use --remove-nested-git or --preserve-upstream-git. Aborting."
    exit 1
  fi
else
  echo "No nested .git found under android_companion — proceeding"
fi

# Step 2: update app/build.gradle applicationId line if present
APP_GRADLE="$ANDROID_APP_DIR/app/build.gradle"
if [ -f "$APP_GRADLE" ]; then
  if grep -q "applicationId" "$APP_GRADLE"; then
    echo "Updating applicationId in $APP_GRADLE -> $NEW_APP_ID"
    sed -E -i.bak "s/^\s*applicationId\s+.*$/    applicationId '$NEW_APP_ID'/" "$APP_GRADLE"
  else
    echo "No applicationId found in $APP_GRADLE — add manually if needed"
  fi
else
  echo "App-level build.gradle not found at $APP_GRADLE"
fi

# Step 3: update AndroidManifest package attribute
MANIFEST="$ANDROID_APP_DIR/app/src/main/AndroidManifest.xml"
if [ -f "$MANIFEST" ]; then
  echo "Updating AndroidManifest package attribute to $NEW_APP_ID"
  sed -E -i.bak "s/package=\"[^"]+\"/package=\"$NEW_APP_ID\"/" "$MANIFEST"
else
  echo "AndroidManifest not found at $MANIFEST"
fi

# Step 4: update Kotlin package declarations and move sources
OLD_PKG_DIR="$APP_SRC_JAVA_DIR/$OLD_PKG_PATH"
NEW_PKG_DIR="$APP_SRC_JAVA_DIR/$NEW_PKG_PATH"
if [ -d "$OLD_PKG_DIR" ]; then
  echo "Updating Kotlin package lines under $OLD_PKG_DIR"
  find "$OLD_PKG_DIR" -type f -name "*.kt" -print0 | xargs -0 -n1 sed -i.bak "s/^package $OLD_APP_ID/package $NEW_APP_ID/"

  echo "Creating new package dir $NEW_PKG_DIR"
  mkdir -p "$NEW_PKG_DIR"
  echo "Moving sources to new package dir"
  rsync -a "$OLD_PKG_DIR/" "$NEW_PKG_DIR/"
  rm -rf "$OLD_PKG_DIR"
else
  echo "Old package directory $OLD_PKG_DIR not found — skipping source move"
fi

# Step 5: global replacements in Android app sources
echo "Replacing remaining occurrences of $OLD_APP_ID with $NEW_APP_ID in android app sources"
grep -RIl "$OLD_APP_ID" "$ANDROID_APP_DIR/app" || true | xargs -r sed -i.bak "s|$OLD_APP_ID|$NEW_APP_ID|g"

# Step 6: generate gradle wrapper if possible
if [ -x "$(command -v gradle 2>/dev/null || true)" ]; then
  echo "Generating Gradle wrapper using system gradle"
  (cd "$ANDROID_APP_DIR" && gradle wrapper || true)
else
  echo "No system gradle found; wrapper generation skipped. You can run 'gradle wrapper' or use Android Studio to generate the wrapper."
fi

# Step 7: optionally commit
if [ "$COMMIT" -eq 1 ]; then
  echo "Staging and committing changes"
  git add -A android_companion
  if ! git commit -m "Import android_companion upstream app: merge sources, set applicationId to $NEW_APP_ID [skip ci]"; then
    echo "No changes to commit or commit failed"
  else
    echo "Commit complete"
  fi
else
  echo "Changes prepared — not committed (use --commit to enable automatic commit)"
fi

echo "Import complete — review changes and run the Android build (./gradlew assembleDebug) to validate."
