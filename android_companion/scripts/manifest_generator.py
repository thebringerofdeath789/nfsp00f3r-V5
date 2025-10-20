#!/usr/bin/env python3
"""
Project Manifest Generator for nfsp00f3r-V5
Auto-generate project manifests and batch configurations from README and codebase.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set
import yaml
import json
from datetime import datetime

class ManifestGenerator:
    """Auto-generate project structure and batching manifests."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.android_app_path = self.workspace_root / "android-app"

    def generate_all_manifests(self) -> Dict:
        """Generate complete project manifests."""
        print("📄 Generating project manifests...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "project_manifest": self.generate_project_manifest(),
            "batch_configuration": self.generate_batch_config(),
            "dependency_manifest": self.generate_dependency_manifest(),
            "feature_extraction": self.extract_features_from_readme()
        }

        self.save_manifests(results)
        return results

    def generate_project_manifest(self) -> Dict:
        """Generate comprehensive project manifest."""
        android_files = self.analyze_android_structure()

        return {
            "project_info": {
                "name": "nfsp00f3r-V5",
                "package": "com.nf-sp00f.app",
                "version": "0.1.0",
                "description": "Advanced EMV Security Research Platform for Android",
                "platform": "Android 14+, Kotlin, Jetpack Compose Material3",
                "min_sdk": 28
            },
            "architecture": {
                "layers": [
                    "ui (Compose fragments)",
                    "cardreading (NFC/PN532 patterns)",
                    "emulation (HCE + attack profiles)",
                    "data (EMV models + persistence)",
                    "utils (TLV + hex helpers)"
                ],
                "communication_protocol": "ByteArray for APDU exchanges",
                "parsing_strategy": "Dynamic PDOL/CDOL from BER-TLV"
            },
            "android_structure": android_files,
            "quality_requirements": {
                "corruption_protocol": "DELETE→REGENERATE",
                "safe_call_operators": "forbidden",
                "build_requirement": "BUILD SUCCESSFUL for task completion",
                "naming_conventions": "PascalCase classes, camelCase methods"
            }
        }

    def generate_batch_config(self) -> Dict:
        """Generate efficient batching configuration."""
        return {
            "batching_strategy": {
                "max_tasks_per_batch": 5,
                "atomic_operations": True,
                "efficiency_focus": "minimize API calls"
            },
            "batches": [
                {
                    "id": "batch_1",
                    "name": "EMV Data Models",
                    "priority": 1,
                    "tasks": [
                        "Create EmvCardData.kt with 70+ EMV tags",
                        "Implement ApduLogEntry for real-time logging",
                        "Build CardProfile with persistence",
                        "Add TLV parsing utilities",
                        "Verify BUILD SUCCESSFUL"
                    ]
                },
                {
                    "id": "batch_2",
                    "name": "NFC Reading Engine",
                    "priority": 2,
                    "tasks": [
                        "Implement NfcCardReaderWithWorkflows",
                        "Add dynamic PDOL/CDOL construction",
                        "Integrate BER-TLV parsing with payneteasy library",
                        "Create 6 EMV workflow presets",
                        "Test NFC pipeline end-to-end"
                    ]
                },
                {
                    "id": "batch_3",
                    "name": "HCE Emulation System",
                    "priority": 3,
                    "tasks": [
                        "Create EnhancedHceService for Android HCE",
                        "Build EmvAttackEmulationManager coordinator",
                        "Implement 5 EmulationProfiles (PPSE, AIP, Track2, Cryptogram, CVM)",
                        "Add attack validation and safety checks",
                        "Test HCE emulation with PN532 terminal"
                    ]
                },
                {
                    "id": "batch_4",
                    "name": "UI Implementation",
                    "priority": 4,
                    "tasks": [
                        "Create 5 Material3 Compose fragments",
                        "Implement CardProfileManager singleton",
                        "Add real-time APDU logging UI",
                        "Create professional security research theme",
                        "Wire complete navigation system"
                    ]
                },
                {
                    "id": "batch_5",
                    "name": "Integration & Testing",
                    "priority": 5,
                    "tasks": [
                        "Full end-to-end EMV workflow testing",
                        "PN532 hardware integration validation",
                        "Performance benchmarking and optimization",
                        "Security audit and vulnerability assessment",
                        "Release preparation and APK generation"
                    ]
                }
            ]
        }

    def generate_dependency_manifest(self) -> Dict:
        """Generate comprehensive dependency requirements."""
        return {
            "android_dependencies": {
                "compose": [
                    "androidx.compose.material3:material3",
                    "androidx.navigation:navigation-compose",
                    "androidx.lifecycle:lifecycle-viewmodel-compose"
                ],
                "emv": [
                    "com.payneteasy:ber-tlv:1.0-11"
                ],
                "logging": [
                    "com.jakewharton.timber:timber"
                ],
                "testing": [
                    "junit:junit:4.13.2",
                    "androidx.test.ext:junit:1.1.5"
                ]
            },
            "system_requirements": {
                "jdk": "/opt/openjdk-bin-17",
                "android_sdk": "/home/user/Android/Sdk",
                "gradle": "8.6",
                "kotlin": "1.9.20+"
            },
            "hardware_requirements": {
                "nfc": "ISO-DEP support required",
                "bluetooth": "For PN532 external hardware (optional)",
                "usb": "For PN532 USB connection (optional)"
            }
        }

    def extract_features_from_readme(self) -> Dict:
        """Extract feature requirements from README.md."""
        readme_path = self.workspace_root / "README.md"

        if not readme_path.exists():
            return {"error": "README.md not found"}

        try:
            content = readme_path.read_text(encoding='utf-8')

            # Extract EMV workflows
            workflow_pattern = r'- (\w+.*?)\((.*?)\)'
            workflows = re.findall(workflow_pattern, content)

            # Extract attack profiles
            attack_pattern = r'\d+\)\s+(\w+.*?)(?:Attack|Profile)'
            attacks = re.findall(attack_pattern, content)

            # Extract UI components
            ui_pattern = r'- (\w+Fragment)'
            ui_components = re.findall(ui_pattern, content)

            return {
                "emv_workflows": workflows[:6] if workflows else [],
                "attack_profiles": attacks[:5] if attacks else [],
                "ui_components": ui_components[:5] if ui_components else [],
                "extraction_successful": True
            }

        except Exception as e:
            return {"error": f"Failed to extract features: {str(e)}"}

    def analyze_android_structure(self) -> Dict:
        """Analyze current Android project structure."""
        if not self.android_app_path.exists():
            return {"error": "Android app directory not found"}

        structure = {
            "kotlin_files": [],
            "resource_files": [],
            "gradle_files": [],
            "manifest_files": []
        }

        try:
            # Find Kotlin source files
            for kt_file in self.android_app_path.rglob("*.kt"):
                relative_path = kt_file.relative_to(self.android_app_path)
                structure["kotlin_files"].append(str(relative_path))

            # Find resource files
            res_path = self.android_app_path / "app" / "src" / "main" / "res"
            if res_path.exists():
                for res_file in res_path.rglob("*.xml"):
                    relative_path = res_file.relative_to(res_path)
                    structure["resource_files"].append(str(relative_path))

            # Find Gradle files
            for gradle_file in self.android_app_path.rglob("*.gradle"):
                relative_path = gradle_file.relative_to(self.android_app_path)
                structure["gradle_files"].append(str(relative_path))

            # Find manifest files
            for manifest_file in self.android_app_path.rglob("AndroidManifest.xml"):
                relative_path = manifest_file.relative_to(self.android_app_path)
                structure["manifest_files"].append(str(relative_path))

        except Exception as e:
            structure["error"] = str(e)

        return structure

    def save_manifests(self, results: Dict):
        """Save generated manifests to files."""
        # Save project manifest as YAML
        project_manifest_path = self.workspace_root / "project_manifest.yaml"
        with open(project_manifest_path, 'w') as f:
            yaml.dump(results["project_manifest"], f, default_flow_style=False, sort_keys=False)

        # Save batch configuration
        batch_config_path = self.workspace_root / "batches.yaml"
        with open(batch_config_path, 'w') as f:
            yaml.dump(results["batch_configuration"], f, default_flow_style=False, sort_keys=False)

        # Save full results as JSON for reference
        full_manifest_path = self.workspace_root / "docs" / "mem" / "generated_manifests.json"
        full_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_manifest_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"✅ Manifests saved:")
        print(f"   📄 {project_manifest_path.name}")
        print(f"   📄 {batch_config_path.name}")
        print(f"   📄 {full_manifest_path.relative_to(self.workspace_root)}")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        workspace_root = sys.argv[1]
    else:
        workspace_root = os.getcwd()

    generator = ManifestGenerator(workspace_root)
    results = generator.generate_all_manifests()

    print("\n📄 Manifest Generation Complete")
    print("="*50)
    print(f"Generated at: {results['timestamp']}")

    if 'error' not in str(results):
        print("✅ All manifests generated successfully")
        sys.exit(0)
    else:
        print("⚠️  Some manifest generation issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()
