#!/usr/bin/env python3
"""
Codebase Audit Tool for nfsp00f3r-V5 EMV Security Platform
Detects file corruption, duplicates, placeholders, and quality issues.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json
from datetime import datetime

class CodebaseAuditor:
    """Comprehensive codebase quality and corruption detection."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.android_app_path = self.workspace_root / "android-app"
        self.issues = []

    def audit_all(self) -> Dict:
        """Run complete audit and return results."""
        print("🔍 Starting comprehensive codebase audit...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "corruption_issues": self.detect_corruption(),
            "duplicate_issues": self.detect_duplicates(),
            "placeholder_issues": self.detect_placeholders(),
            "naming_issues": self.check_naming_conventions(),
            "build_issues": self.check_build_files(),
            "summary": {}
        }

        # Generate summary
        total_issues = sum(len(issues) for issues in results.values() if isinstance(issues, list))
        results["summary"] = {
            "total_issues": total_issues,
            "critical_issues": len(results["corruption_issues"]),
            "status": "PASS" if total_issues == 0 else "ISSUES_FOUND"
        }

        self.print_report(results)
        return results

    def detect_corruption(self) -> List[Dict]:
        """Detect file corruption patterns."""
        corruption_issues = []

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if not kotlin_file.exists():
                continue

            try:
                content = kotlin_file.read_text(encoding='utf-8')

                # Check for multiple import blocks
                import_blocks = len(re.findall(r'^import\s+', content, re.MULTILINE))
                if import_blocks > 10:  # Suspicious threshold
                    corruption_issues.append({
                        "file": str(kotlin_file.relative_to(self.workspace_root)),
                        "type": "multiple_import_blocks",
                        "severity": "CRITICAL",
                        "description": f"Found {import_blocks} import statements, suggests corruption"
                    })

                # Check for duplicate class definitions
                class_matches = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
                if len(class_matches) != len(set(class_matches)):
                    corruption_issues.append({
                        "file": str(kotlin_file.relative_to(self.workspace_root)),
                        "type": "duplicate_classes",
                        "severity": "CRITICAL",
                        "description": f"Duplicate class definitions: {class_matches}"
                    })

                # Check for functions outside class scope (corruption indicator)
                lines = content.split('\n')
                in_class = False
                brace_depth = 0
                for i, line in enumerate(lines):
                    if re.match(r'^class\s+', line.strip()):
                        in_class = True
                        brace_depth = 0

                    brace_depth += line.count('{') - line.count('}')

                    if in_class and brace_depth <= 0 and i > 0:
                        in_class = False

                    if not in_class and re.match(r'^\s*fun\s+', line):
                        corruption_issues.append({
                            "file": str(kotlin_file.relative_to(self.workspace_root)),
                            "type": "function_outside_class",
                            "severity": "CRITICAL",
                            "description": f"Function outside class scope at line {i+1}: {line.strip()[:50]}"
                        })

            except Exception as e:
                corruption_issues.append({
                    "file": str(kotlin_file.relative_to(self.workspace_root)),
                    "type": "read_error",
                    "severity": "ERROR",
                    "description": f"Could not read file: {str(e)}"
                })

        return corruption_issues

    def detect_duplicates(self) -> List[Dict]:
        """Detect duplicate code and files."""
        duplicate_issues = []
        file_hashes = {}

        for code_file in self.android_app_path.rglob("*.kt"):
            if code_file.exists():
                try:
                    content = code_file.read_text(encoding='utf-8')
                    content_hash = hash(content)

                    if content_hash in file_hashes:
                        duplicate_issues.append({
                            "type": "duplicate_files",
                            "severity": "HIGH",
                            "files": [str(file_hashes[content_hash]), str(code_file.relative_to(self.workspace_root))],
                            "description": "Identical file content detected"
                        })
                    else:
                        file_hashes[content_hash] = code_file.relative_to(self.workspace_root)

                except Exception:
                    pass

        return duplicate_issues

    def detect_placeholders(self) -> List[Dict]:
        """Detect placeholder/stub code that violates production standards."""
        placeholder_issues = []
        placeholder_patterns = [
            r'TODO.*',
            r'FIXME.*',
            r'//\s*placeholder',
            r'//\s*stub',
            r'//\s*demo',
            r'//\s*sample',
            r'return\s+null\s*//.*placeholder',
            r'throw\s+NotImplementedError',
            r'fun\s+\w+\(\)\s*{\s*}',  # Empty functions
        ]

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if kotlin_file.exists():
                try:
                    content = kotlin_file.read_text(encoding='utf-8')

                    for pattern in placeholder_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            placeholder_issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": "placeholder_code",
                                "severity": "HIGH",
                                "line": line_num,
                                "description": f"Placeholder code: {match.group()[:50]}"
                            })

                except Exception:
                    pass

        return placeholder_issues

    def check_naming_conventions(self) -> List[Dict]:
        """Check Kotlin naming conventions."""
        naming_issues = []

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if kotlin_file.exists():
                try:
                    content = kotlin_file.read_text(encoding='utf-8')

                    # Check class names (PascalCase)
                    class_matches = re.finditer(r'class\s+(\w+)', content)
                    for match in class_matches:
                        class_name = match.group(1)
                        if not class_name[0].isupper() or '_' in class_name:
                            naming_issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": "class_naming",
                                "severity": "MEDIUM",
                                "description": f"Class '{class_name}' should use PascalCase"
                            })

                    # Check function names (camelCase)
                    func_matches = re.finditer(r'fun\s+(\w+)', content)
                    for match in func_matches:
                        func_name = match.group(1)
                        if func_name[0].isupper() or '_' in func_name:
                            naming_issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": "function_naming",
                                "severity": "MEDIUM",
                                "description": f"Function '{func_name}' should use camelCase"
                            })

                except Exception:
                    pass

        return naming_issues

    def check_build_files(self) -> List[Dict]:
        """Check build configuration integrity."""
        build_issues = []

        # Check gradle files
        gradle_files = ["build.gradle", "settings.gradle", "app/build.gradle"]
        for gradle_file in gradle_files:
            gradle_path = self.android_app_path / gradle_file
            if gradle_path.exists():
                try:
                    content = gradle_path.read_text(encoding='utf-8')

                    # Check for duplicate blocks
                    if gradle_file == "settings.gradle":
                        plugin_blocks = content.count("pluginManagement")
                        if plugin_blocks > 1:
                            build_issues.append({
                                "file": str(gradle_path.relative_to(self.workspace_root)),
                                "type": "duplicate_gradle_blocks",
                                "severity": "HIGH",
                                "description": f"Found {plugin_blocks} pluginManagement blocks"
                            })

                except Exception as e:
                    build_issues.append({
                        "file": str(gradle_path.relative_to(self.workspace_root)),
                        "type": "gradle_read_error",
                        "severity": "ERROR",
                        "description": f"Could not read gradle file: {str(e)}"
                    })

        return build_issues

    def print_report(self, results: Dict):
        """Print formatted audit report."""
        print("\n" + "="*60)
        print("🔍 CODEBASE AUDIT REPORT")
        print("="*60)

        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"📊 Total Issues: {results['summary']['total_issues']}")
        print(f"🚨 Critical Issues: {results['summary']['critical_issues']}")
        print(f"✅ Status: {results['summary']['status']}")

        for category, issues in results.items():
            if isinstance(issues, list) and issues:
                print(f"\n🔸 {category.replace('_', ' ').title()}:")
                for issue in issues[:5]:  # Show first 5 per category
                    severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "📝", "ERROR": "❌"}.get(issue.get('severity', 'MEDIUM'), "📝")
                    print(f"  {severity_emoji} {issue.get('description', 'No description')}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues) - 5} more issues")

        print("\n" + "="*60)

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        workspace_root = sys.argv[1]
    else:
        workspace_root = os.getcwd()

    auditor = CodebaseAuditor(workspace_root)
    results = auditor.audit_all()

    # Exit with error code if issues found
    sys.exit(0 if results["summary"]["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
