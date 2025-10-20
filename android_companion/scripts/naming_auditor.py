#!/usr/bin/env python3
"""
Naming Convention Auditor for nfsp00f3r-V5
Enforces Kotlin/Android naming standards and detects violations.
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime

class NamingAuditor:
    """Enforce naming conventions across the codebase."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.android_app_path = self.workspace_root / "android-app"

    def audit_naming(self) -> Dict:
        """Run complete naming convention audit."""
        print("📝 Auditing naming conventions...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "kotlin_issues": self.check_kotlin_naming(),
            "resource_issues": self.check_resource_naming(),
            "package_issues": self.check_package_naming(),
            "file_issues": self.check_file_naming(),
            "summary": {}
        }

        total_issues = sum(len(issues) for issues in results.values() if isinstance(issues, list))
        results["summary"] = {
            "total_violations": total_issues,
            "status": "COMPLIANT" if total_issues == 0 else "VIOLATIONS_FOUND"
        }

        self.print_report(results)
        return results

    def check_kotlin_naming(self) -> List[Dict]:
        """Check Kotlin naming conventions."""
        issues = []

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if not kotlin_file.exists():
                continue

            try:
                content = kotlin_file.read_text(encoding='utf-8')
                relative_path = str(kotlin_file.relative_to(self.workspace_root))

                # Classes should be PascalCase
                for match in re.finditer(r'(?:class|interface|object)\s+(\w+)', content):
                    name = match.group(1)
                    if not self.is_pascal_case(name):
                        issues.append({
                            "file": relative_path,
                            "type": "class_naming",
                            "severity": "HIGH",
                            "name": name,
                            "expected": self.to_pascal_case(name),
                            "description": f"Class/Interface '{name}' should be PascalCase"
                        })

                # Functions should be camelCase
                for match in re.finditer(r'fun\s+(\w+)', content):
                    name = match.group(1)
                    if not self.is_camel_case(name) and name not in ['onCreate', 'onResume', 'onPause']:  # Android lifecycle exceptions
                        issues.append({
                            "file": relative_path,
                            "type": "function_naming",
                            "severity": "MEDIUM",
                            "name": name,
                            "expected": self.to_camel_case(name),
                            "description": f"Function '{name}' should be camelCase"
                        })

                # Properties should be camelCase
                for match in re.finditer(r'(?:val|var)\s+(\w+)', content):
                    name = match.group(1)
                    if not self.is_camel_case(name):
                        issues.append({
                            "file": relative_path,
                            "type": "property_naming",
                            "severity": "MEDIUM",
                            "name": name,
                            "expected": self.to_camel_case(name),
                            "description": f"Property '{name}' should be camelCase"
                        })

                # Constants should be UPPER_SNAKE_CASE
                for match in re.finditer(r'const\s+val\s+(\w+)', content):
                    name = match.group(1)
                    if not self.is_upper_snake_case(name):
                        issues.append({
                            "file": relative_path,
                            "type": "constant_naming",
                            "severity": "MEDIUM",
                            "name": name,
                            "expected": self.to_upper_snake_case(name),
                            "description": f"Constant '{name}' should be UPPER_SNAKE_CASE"
                        })

                # Check for safe call operators (forbidden per rules)
                safe_call_matches = re.finditer(r'\?\.((?!let|run|apply|also)\w+)', content)
                for match in safe_call_matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        "file": relative_path,
                        "type": "safe_call_operator",
                        "severity": "CRITICAL",
                        "line": line_num,
                        "description": f"Safe call operator forbidden: {match.group()}"
                    })

            except Exception as e:
                issues.append({
                    "file": relative_path,
                    "type": "file_error",
                    "severity": "ERROR",
                    "description": f"Could not analyze file: {str(e)}"
                })

        return issues

    def check_resource_naming(self) -> List[Dict]:
        """Check Android resource naming conventions."""
        issues = []

        res_path = self.android_app_path / "app" / "src" / "main" / "res"
        if not res_path.exists():
            return issues

        # Layout files should be lowercase_with_underscores
        for layout_file in res_path.rglob("layout/*.xml"):
            name = layout_file.stem
            if not self.is_lower_snake_case(name):
                issues.append({
                    "file": str(layout_file.relative_to(self.workspace_root)),
                    "type": "layout_naming",
                    "severity": "MEDIUM",
                    "name": name,
                    "expected": self.to_lower_snake_case(name),
                    "description": f"Layout '{name}' should be lowercase_with_underscores"
                })

        # Drawable files should be lowercase_with_underscores
        for drawable_file in res_path.rglob("drawable*/*.xml"):
            name = drawable_file.stem
            if not self.is_lower_snake_case(name):
                issues.append({
                    "file": str(drawable_file.relative_to(self.workspace_root)),
                    "type": "drawable_naming",
                    "severity": "MEDIUM",
                    "name": name,
                    "expected": self.to_lower_snake_case(name),
                    "description": f"Drawable '{name}' should be lowercase_with_underscores"
                })

        return issues

    def check_package_naming(self) -> List[Dict]:
        """Check package naming conventions."""
        issues = []

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if not kotlin_file.exists():
                continue

            try:
                content = kotlin_file.read_text(encoding='utf-8')

                # Extract package declaration
                package_match = re.search(r'package\s+([\w.]+)', content)
                if package_match:
                    package_name = package_match.group(1)

                    # Package should start with expected prefix
                    if not package_name.startswith('com.nf-sp00f.app'):
                        issues.append({
                            "file": str(kotlin_file.relative_to(self.workspace_root)),
                            "type": "package_prefix",
                            "severity": "HIGH",
                            "name": package_name,
                            "description": f"Package should start with 'com.nf-sp00f.app'"
                        })

                    # Package components should be lowercase
                    for component in package_name.split('.'):
                        if not component.islower() or '_' in component:
                            issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": "package_case",
                                "severity": "MEDIUM",
                                "name": package_name,
                                "description": f"Package component '{component}' should be lowercase"
                            })

            except Exception:
                pass

        return issues

    def check_file_naming(self) -> List[Dict]:
        """Check file naming conventions."""
        issues = []

        # Kotlin files should match class name or be descriptive
        for kotlin_file in self.android_app_path.rglob("*.kt"):
            file_name = kotlin_file.stem

            # Should be PascalCase for class files
            if not self.is_pascal_case(file_name) and not file_name.endswith('Extensions'):
                # Check if it contains a class with matching name
                try:
                    content = kotlin_file.read_text(encoding='utf-8')
                    class_matches = re.findall(r'(?:class|interface|object)\s+(\w+)', content)

                    if class_matches and file_name not in class_matches:
                        issues.append({
                            "file": str(kotlin_file.relative_to(self.workspace_root)),
                            "type": "file_class_mismatch",
                            "severity": "MEDIUM",
                            "name": file_name,
                            "classes": class_matches,
                            "description": f"File name '{file_name}' doesn't match class names {class_matches}"
                        })
                except Exception:
                    pass

        return issues

    # Utility methods for case checking and conversion
    def is_pascal_case(self, name: str) -> bool:
        return name[0].isupper() and '_' not in name and name.isalnum()

    def is_camel_case(self, name: str) -> bool:
        return name[0].islower() and '_' not in name and name.isalnum()

    def is_upper_snake_case(self, name: str) -> bool:
        return name.isupper() and all(c.isalnum() or c == '_' for c in name)

    def is_lower_snake_case(self, name: str) -> bool:
        return name.islower() and all(c.isalnum() or c == '_' for c in name)

    def to_pascal_case(self, name: str) -> str:
        return ''.join(word.capitalize() for word in re.split(r'[_\-\s]+', name))

    def to_camel_case(self, name: str) -> str:
        words = re.split(r'[_\-\s]+', name)
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

    def to_upper_snake_case(self, name: str) -> str:
        return re.sub(r'([A-Z])', r'_\1', name).upper().lstrip('_')

    def to_lower_snake_case(self, name: str) -> str:
        return re.sub(r'([A-Z])', r'_\1', name).lower().lstrip('_')

    def print_report(self, results: Dict):
        """Print formatted naming report."""
        print("\n" + "="*60)
        print("📝 NAMING CONVENTION AUDIT REPORT")
        print("="*60)

        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"📊 Total Violations: {results['summary']['total_violations']}")
        print(f"✅ Status: {results['summary']['status']}")

        for category, issues in results.items():
            if isinstance(issues, list) and issues:
                print(f"\n🔸 {category.replace('_', ' ').title()}:")
                for issue in issues[:3]:  # Show first 3 per category
                    severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "📝", "ERROR": "❌"}.get(issue.get('severity', 'MEDIUM'), "📝")
                    print(f"  {severity_emoji} {issue.get('description', 'No description')}")
                    if 'expected' in issue:
                        print(f"      💡 Suggested: {issue['expected']}")
                if len(issues) > 3:
                    print(f"  ... and {len(issues) - 3} more violations")

        print("\n" + "="*60)

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        workspace_root = sys.argv[1]
    else:
        workspace_root = os.getcwd()

    auditor = NamingAuditor(workspace_root)
    results = auditor.audit_naming()

    # Exit with error code if violations found
    sys.exit(0 if results["summary"]["status"] == "COMPLIANT" else 1)

if __name__ == "__main__":
    main()
