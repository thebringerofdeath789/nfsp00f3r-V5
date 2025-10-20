<#
import-android-into-repo.ps1

Purpose:
- Remove the nested upstream `.git` from `android_companion/` (or preserve it
  by moving to a backup location).
- Rename package/applicationId from upstream value to this repo's chosen
  application id (default: com.emvresearch.nfsp00f3rV5c).
- Move Kotlin source files into the new package folder and update `package`
  declarations inside `.kt` files.
- Update `AndroidManifest.xml` and `app/build.gradle` applicationId.
- Optionally generate the Gradle wrapper and commit the imported files into
  the parent repository.

USAGE (from project root or run directly):
  # Dry-run: shows what will change
  .\android_companion\android-app\scripts\import-android-into-repo.ps1 -DryRun

  # Perform changes, remove nested .git and commit
  .\android_companion\android-app\scripts\import-android-into-repo.ps1 -RemoveNestedGit -Commit

  # Preserve upstream .git by moving it to docs/backups
  .\android_companion\android-app\scripts\import-android-into-repo.ps1 -PreserveUpstreamGit -Commit

NOTE: This script performs filesystem operations and (optionally) git commits.
Make a backup or run with -DryRun first. The script requires PowerShell and
Git to be available in PATH when using -Commit.
#>

param(
    [string]$NewApplicationId = "com.emvresearch.nfsp00f3rV5c",
    [string]$OldApplicationId = "com.nf_sp00f.app",
    [switch]$RemoveNestedGit,
    [switch]$PreserveUpstreamGit,
    [switch]$Commit,
    [switch]$DryRun
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    # scriptDir = android_companion/android-app/scripts
    $androidCompanionDir = Resolve-Path (Join-Path $scriptDir "..\..")
    $androidAppDir = Resolve-Path (Join-Path $androidCompanionDir "android-app")
    $appSrcJavaDir = Join-Path $androidAppDir.FullName "app\src\main\java"

    Write-Info "Detected android_companion dir: $($androidCompanionDir)"
    Write-Info "Detected android-app dir: $($androidAppDir)"

    # Compute old/new package filesystem paths
    $oldPkgRelative = $OldApplicationId -replace '\.', '\\'
    $newPkgRelative = $NewApplicationId -replace '\.', '\\'
    $oldPkgFullPath = Join-Path $appSrcJavaDir $oldPkgRelative
    $newPkgFullPath = Join-Path $appSrcJavaDir $newPkgRelative

    if (-not (Test-Path $oldPkgFullPath)) {
        Write-Warn "Old package directory not found at: $oldPkgFullPath";
        Write-Warn "Proceeding may still be useful (some files might be elsewhere)."
    }

    if ($DryRun) {
        Write-Info "DRY RUN: The following actions would be performed:";
        Write-Info " - Replace applicationId '$OldApplicationId' -> '$NewApplicationId' in app/build.gradle"
        Write-Info " - Replace manifest package value and update package declarations inside Kotlin files"
        Write-Info " - Move Kotlin sources from '$oldPkgRelative' -> '$newPkgRelative' (if present)"
        if ($RemoveNestedGit) { Write-Info " - Remove nested .git under android_companion" } else { Write-Info " - Leave nested .git in place" }
        if ($PreserveUpstreamGit) { Write-Info " - Move nested .git to docs/backups/android_companion_upstream_git (preserve upstream history)" }
        if ($Commit) { Write-Info " - Stage & commit the changes to the parent git repository" } else { Write-Info " - No git commit will be performed (use -Commit to enable)" }
        Write-Info "Run without -DryRun to perform the actions."
        exit 0
    }

    # Step 1: Handle nested .git
    $nestedGit = Join-Path $androidCompanionDir.FullName ".git"
    if (Test-Path $nestedGit) {
        if ($PreserveUpstreamGit) {
            $backupDir = Join-Path (Join-Path $androidCompanionDir.FullName "..\docs\backups") "android_companion_upstream_git"
            Write-Info "Preserving nested .git to: $backupDir"
            New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
            Move-Item -Path $nestedGit -Destination $backupDir -Force
        } elseif ($RemoveNestedGit) {
            Write-Info "Removing nested .git at: $nestedGit"
            Remove-Item -Recurse -Force -LiteralPath $nestedGit
        } else {
            Write-Warn "Nested .git detected at $nestedGit. Use -RemoveNestedGit to remove it or -PreserveUpstreamGit to move it to docs/backups. Aborting.";
            exit 1
        }
    } else {
        Write-Info "No nested .git found under android_companion — nothing to remove."
    }

    # Step 2: Replace applicationId in app/build.gradle (module)
    $appGradle = Join-Path $androidAppDir.FullName "app\build.gradle"
    if (Test-Path $appGradle) {
        $gradleText = Get-Content -Raw -LiteralPath $appGradle
        # Match the applicationId line (be permissive) and replace the entire line
        $pattern = '(?m)^\s*applicationId\s+.*$'
        if ($gradleText -match $pattern) {
            $newLine = "applicationId '$NewApplicationId'"
            $newGradleText = [regex]::Replace($gradleText, $pattern, $newLine)
            Set-Content -LiteralPath $appGradle -Value $newGradleText
            Write-Info "Updated applicationId in app/build.gradle to '$NewApplicationId'"
        } else {
            Write-Warn "No applicationId found in $appGradle — you may need to update it manually."
        }
    } else { Write-Warn "App-level build.gradle not found at expected location: $appGradle" }

    # Step 3: Update AndroidManifest package attribute (if present)
    $manifest = Join-Path $androidAppDir.FullName "app\src\main\AndroidManifest.xml"
    if (Test-Path $manifest) {
        $mtext = Get-Content -Raw -LiteralPath $manifest
    $mtextNew = $mtext -replace 'package\s*=\s*"[^"]+"', ('package="' + $NewApplicationId + '"')
        Set-Content -LiteralPath $manifest -Value $mtextNew
        Write-Info "Updated AndroidManifest package attribute to '$NewApplicationId'"
    } else { Write-Warn "AndroidManifest.xml not found at expected path: $manifest" }

    # Step 4: Update package declarations inside Kotlin files and move sources
    if (Test-Path $oldPkgFullPath) {
        Write-Info "Updating package declarations and moving Kotlin sources..."
        $ktFiles = Get-ChildItem -Path $oldPkgFullPath -Filter *.kt -Recurse -File
        foreach ($f in $ktFiles) {
            $text = Get-Content -Raw -LiteralPath $f.FullName
            $text = $text -replace "package\s+${OldApplicationId}", "package $NewApplicationId"
            Set-Content -LiteralPath $f.FullName -Value $text
        }

        # Ensure new package directory exists
        if (-not (Test-Path $newPkgFullPath)) { New-Item -ItemType Directory -Force -Path $newPkgFullPath | Out-Null }

        # Move files preserving relative structure
        $allFiles = Get-ChildItem -Path $oldPkgFullPath -Recurse -File
        foreach ($src in $allFiles) {
            $rel = $src.FullName.Substring($oldPkgFullPath.Length).TrimStart('\')
            $dest = Join-Path $newPkgFullPath $rel
            $destDir = Split-Path -Parent $dest
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }
            Move-Item -LiteralPath $src.FullName -Destination $dest -Force
        }

        # Delete old package tree if empty
        try {
            Remove-Item -LiteralPath $oldPkgFullPath -Recurse -Force -ErrorAction SilentlyContinue
        } catch { }

        Write-Info "Moved Kotlin sources from '$oldPkgRelative' -> '$newPkgRelative'"
    } else {
        Write-Warn "Old package folder '$oldPkgRelative' not found, skipping source move"
    }

    # Step 5: Global replace of occurrences of the old application id in source files
    Write-Info "Searching for other occurrences of '$OldApplicationId' in the Android app and replacing with '$NewApplicationId'"
    $searchFiles = Get-ChildItem -Path (Join-Path $androidAppDir.FullName 'app') -Recurse -File -Include *.kt,*.xml,*.gradle,*.kts
    foreach ($sf in $searchFiles) {
        $txt = Get-Content -Raw -LiteralPath $sf.FullName
        if ($txt -like "*${OldApplicationId}*") {
            $newtxt = $txt -replace [regex]::Escape($OldApplicationId), $NewApplicationId
            Set-Content -LiteralPath $sf.FullName -Value $newtxt
        }
    }

    # Step 6: Optionally generate Gradle wrapper by delegating to existing helper
    $wrapperScript = Join-Path $androidAppDir.FullName "scripts\generate-gradle-wrapper.ps1"
    if (Test-Path $wrapperScript) {
        Write-Info "Invoking Gradle wrapper generation helper: $wrapperScript"
        & $wrapperScript -Force
    } else {
        Write-Warn "Gradle wrapper helper not found at $wrapperScript — you may need to run 'gradle wrapper' manually or use Android Studio to generate it."
    }

    # Step 7: Optionally commit changes to parent repo
    if ($Commit) {
        $workspaceRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")
        Write-Info "Staging changes and committing from workspace root: $workspaceRoot"
        Push-Location $workspaceRoot
        try {
            & git add -A android_companion
            & git commit -m "Import android_companion upstream app: merge sources, set applicationId to $NewApplicationId [skip ci]"
            if ($LASTEXITCODE -ne 0) { Write-Info "No changes to commit or commit failed" } else { Write-Info "Commit complete" }
        } finally { Pop-Location }
    } else {
        Write-Info "Changes prepared — not committed (use -Commit to enable automatic commit)"
    }

    Write-Info "Import operation complete. Review changes, run a build (./gradlew assembleDebug) and run tests."
} catch {
    Write-Err "Unexpected error: $_"
    exit 1
}
