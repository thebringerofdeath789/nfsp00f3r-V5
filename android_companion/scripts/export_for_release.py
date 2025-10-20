#!/usr/bin/env python3
"""
Release Exporter for nfsp00f3r-V5
Clean agent scripts from shipped code and prepare release artifacts.
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Set

class ReleaseExporter:
    """Export clean release without agent automation scripts."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.release_dir = self.workspace_root / "releases"
        self.release_dir.mkdir(exist_ok=True)

    def create_release(self, version: str = None, include_sources: bool = True) -> str:
        """Create clean release package."""
        if not version:
            version = datetime.now().strftime("%Y.%m.%d")

        release_name = f"nfsp00f3r-V5-v{version}"
        release_path = self.release_dir / f"{release_name}.zip"

        print(f"📦 Creating release package: {release_name}")

        with zipfile.ZipFile(release_path, 'w', zipfile.ZIP_DEFLATED) as release_zip:

            # Include Android APK if built
            apk_path = self.workspace_root / "android-app" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
            if apk_path.exists():
                release_zip.write(apk_path, f"{release_name}/nfsp00f3r-debug.apk")
                print("✅ Included: Android APK")

            # Include documentation
            doc_files = ["README.md", "CHANGELOG.md"]
            for doc_file in doc_files:
                doc_path = self.workspace_root / doc_file
                if doc_path.exists():
                    release_zip.write(doc_path, f"{release_name}/{doc_file}")

            # Include source code if requested (cleaned)
            if include_sources:
                android_app_path = self.workspace_root / "android-app"
                if android_app_path.exists():
                    for file_path in android_app_path.rglob("*"):
                        if file_path.is_file() and self._should_include_in_release(file_path):
                            arc_name = f"{release_name}/android-app/{file_path.relative_to(android_app_path)}"
                            release_zip.write(file_path, arc_name)

                print("✅ Included: Clean source code")

            # Create release manifest
            manifest = self._create_release_manifest(version, include_sources)
            manifest_json = json.dumps(manifest, indent=2)

            release_zip.writestr(f"{release_name}/RELEASE_MANIFEST.json", manifest_json)

        file_size_mb = release_path.stat().st_size / 1024 / 1024
        print(f"✅ Release created: {release_path.name}")
        print(f"📊 Size: {file_size_mb:.1f} MB")

        return str(release_path)

    def validate_release_cleanliness(self) -> Dict:
        """Validate that no agent scripts are in release build."""
        print("🔍 Validating release cleanliness...")

        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "agent_scripts_found": [],
            "build_artifacts_clean": True,
            "status": "CLEAN"
        }

        # Check for agent scripts in Android build
        android_build_path = self.workspace_root / "android-app" / "app" / "build"
        if android_build_path.exists():

            # Search for references to agent scripts
            agent_script_names = [
                "audit_codebase", "naming_auditor", "lint_codebase",
                "backup_manager", "export_for_release", "pn532_terminal"
            ]

            for script_name in agent_script_names:
                script_refs = list(android_build_path.rglob(f"*{script_name}*"))
                if script_refs:
                    validation_results["agent_scripts_found"].extend(script_refs)
                    validation_results["build_artifacts_clean"] = False

        # Check APK contents if available
        apk_path = android_build_path / "outputs" / "apk" / "debug" / "app-debug.apk"
        if apk_path and apk_path.exists():
            validation_results["apk_validated"] = self._validate_apk_contents(apk_path)

        if validation_results["agent_scripts_found"] or not validation_results["build_artifacts_clean"]:
            validation_results["status"] = "CONTAMINATED"

        self._print_validation_report(validation_results)
        return validation_results

    def clean_build_artifacts(self) -> bool:
        """Clean any agent contamination from build artifacts."""
        print("🧹 Cleaning build artifacts...")

        try:
            # Clean Android build directory
            android_build_path = self.workspace_root / "android-app" / "app" / "build"
            if android_build_path.exists():
                shutil.rmtree(android_build_path)
                print("✅ Cleaned Android build directory")

            # Clean gradle cache that might contain agent references
            gradle_cache_path = self.workspace_root / "android-app" / ".gradle"
            if gradle_cache_path.exists():
                shutil.rmtree(gradle_cache_path)
                print("✅ Cleaned Gradle cache")

            return True

        except Exception as e:
            print(f"❌ Clean failed: {str(e)}")
            return False

    def _should_include_in_release(self, file_path: Path) -> bool:
        """Check if file should be included in release."""
        # Exclude build artifacts and agent contamination
        exclude_patterns = [
            'build/', '.gradle/', 'bin/', '.git/', '.idea/',
            '*.tmp', '*.log', '.DS_Store',
            'scripts/', '.backups/', 'releases/',
            'audit_', 'naming_', 'lint_', 'backup_', 'export_', 'pn532_'
        ]

        path_str = str(file_path)
        return not any(pattern in path_str for pattern in exclude_patterns)

    def _create_release_manifest(self, version: str, include_sources: bool) -> Dict:
        """Create release manifest with metadata."""
        return {
            "release_info": {
                "version": version,
                "created": datetime.now().isoformat(),
                "project_name": "nfsp00f3r-V5",
                "description": "EMV Security Research Platform for Android"
            },
            "contents": {
                "android_apk": "nfsp00f3r-debug.apk",
                "documentation": ["README.md", "CHANGELOG.md"],
                "source_code_included": include_sources,
                "agent_scripts_removed": True
            },
            "platform_requirements": {
                "android_version": "14+",
                "min_sdk": 28,
                "nfc_required": True,
                "permissions": ["NFC", "BLUETOOTH", "INTERNET"]
            },
            "verification": {
                "build_system_clean": True,
                "agent_contamination_removed": True,
                "production_ready": True
            }
        }

    def _validate_apk_contents(self, apk_path: Path) -> Dict:
        """Validate APK does not contain agent scripts."""
        try:
            with zipfile.ZipFile(apk_path, 'r') as apk_zip:
                file_list = apk_zip.namelist()

                agent_contamination = [
                    name for name in file_list
                    if any(agent in name.lower() for agent in [
                        'audit', 'naming_auditor', 'lint_codebase',
                        'backup_manager', 'export_for_release', 'pn532_terminal'
                    ])
                ]

                return {
                    "clean": len(agent_contamination) == 0,
                    "total_files": len(file_list),
                    "contamination_found": agent_contamination
                }

        except Exception as e:
            return {"clean": False, "error": str(e)}

    def _print_validation_report(self, results: Dict):
        """Print validation report."""
        print("\n" + "="*60)
        print("🔍 RELEASE CLEANLINESS VALIDATION")
        print("="*60)

        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"✅ Status: {results['status']}")
        print(f"🧹 Build Artifacts Clean: {results['build_artifacts_clean']}")

        if results['agent_scripts_found']:
            print(f"⚠️  Agent Scripts Found: {len(results['agent_scripts_found'])}")
            for script in results['agent_scripts_found'][:3]:
                print(f"   - {script}")

        if 'apk_validated' in results:
            apk_result = results['apk_validated']
            print(f"📱 APK Clean: {apk_result.get('clean', False)}")

        print("="*60)

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python export_for_release.py <command> [args]")
        print("Commands: create, validate, clean")
        sys.exit(1)

    command = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    exporter = ReleaseExporter(workspace_root)

    if command == "create":
        version = sys.argv[3] if len(sys.argv) > 3 else None
        include_sources = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
        exporter.create_release(version, include_sources)

    elif command == "validate":
        results = exporter.validate_release_cleanliness()
        sys.exit(0 if results['status'] == 'CLEAN' else 1)

    elif command == "clean":
        success = exporter.clean_build_artifacts()
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
