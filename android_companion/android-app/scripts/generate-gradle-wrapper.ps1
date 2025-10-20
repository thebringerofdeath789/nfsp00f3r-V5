<#
Generate the Gradle wrapper for the Android app on Windows.

Usage:
  - Run this script from a PowerShell prompt on Windows that has Gradle in PATH
    (or install Gradle via Chocolatey: choco install gradle -y).
  - Example: .\generate-gradle-wrapper.ps1

If the wrapper JAR is already present this script will exit successfully.
If a wrapper is generated, consider committing the generated files so the
project can be built using the checked-in wrapper on other machines.
#>

param(
    [switch]$Force
)

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $projectDir = Resolve-Path (Join-Path $scriptDir "..")
    $wrapperJar = Join-Path $projectDir "gradle\wrapper\gradle-wrapper.jar"

    if (-not (Test-Path $wrapperJar) -or $Force) {
        Write-Host "Gradle wrapper missing or Force requested. Attempting to generate..."

        $gradleCmd = Get-Command gradle -ErrorAction SilentlyContinue
        if (-not $gradleCmd) {
            Write-Host "No 'gradle' command found in PATH."
            Write-Host "Install Gradle (https://gradle.org/install/) or use Chocolatey: choco install gradle -y"
            Write-Host "Alternatively open the project in Android Studio and use the IDE to generate the Gradle wrapper."
            exit 1
        }

        Push-Location $projectDir
        try {
            gradle wrapper
        } finally {
            Pop-Location
        }

        if (Test-Path $wrapperJar) {
            Write-Host "Gradle wrapper generated successfully: $wrapperJar"
            exit 0
        } else {
            Write-Host "Failed to generate Gradle wrapper."
            exit 2
        }
    } else {
        Write-Host "Gradle wrapper already present: $wrapperJar"
        exit 0
    }
} catch {
    Write-Error "Unexpected error while trying to generate the Gradle wrapper: $_"
    exit 3
}
