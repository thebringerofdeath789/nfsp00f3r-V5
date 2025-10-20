#!/usr/bin/env python3
"""
Code Quality and Style Checker for nfsp00f3r-V5
Static analysis and style validation (info-only per policy).
"""
import re
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime

class CodeQualityChecker:
    """Static analysis and code quality validation."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.android_app_path = self.workspace_root / "android-app"

    def check_quality(self) -> Dict:
        """Run code quality analysis."""
        print("🔍 Running code quality analysis...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "complexity_issues": self.check_complexity(),
            "documentation_issues": self.check_documentation(),
            "security_issues": self.check_security_patterns(),
            "performance_issues": self.check_performance(),
            "summary": {}
        }

        total_issues = sum(len(issues) for issues in results.values() if isinstance(issues, list))
        results["summary"] = {
            "total_suggestions": total_issues,
            "status": "ANALYZED"
        }

        self.print_report(results)
        return results

    def check_complexity(self) -> List[Dict]:
        """Check for overly complex functions."""
        issues = []

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if not kotlin_file.exists():
                continue

            try:
                content = kotlin_file.read_text(encoding='utf-8')
                lines = content.split('\n')

                # Find functions and analyze complexity
                in_function = False
                function_name = ""
                brace_depth = 0
                line_count = 0

                for i, line in enumerate(lines):
                    if re.match(r'\s*fun\s+(\w+)', line):
                        if in_function and line_count > 50:
                            issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": "function_length",
                                "severity": "INFO",
                                "function": function_name,
                                "lines": line_count,
                                "description": f"Function '{function_name}' is {line_count} lines (consider splitting)"
                            })

                        function_match = re.search(r'fun\s+(\w+)', line)
                        function_name = function_match.group(1) if function_match else "unknown"
                        in_function = True
                        brace_depth = 0
                        line_count = 0

                    if in_function:
                        line_count += 1
                        brace_depth += line.count('{') - line.count('}')

                        if brace_depth <= 0 and '{' in line:
                            in_function = False

            except Exception:
                pass

        return issues

    def check_documentation(self) -> List[Dict]:
        """Check documentation completeness."""
        issues = []

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if not kotlin_file.exists():
                continue

            try:
                content = kotlin_file.read_text(encoding='utf-8')

                # Check for public classes without KDoc
                class_matches = re.finditer(r'(class|interface)\s+(\w+)', content)
                for match in class_matches:
                    class_name = match.group(2)
                    class_start = match.start()

                    # Look for KDoc comment before class
                    preceding_text = content[:class_start]
                    if not re.search(r'/\*\*.*\*/\s*$', preceding_text, re.DOTALL):
                        issues.append({
                            "file": str(kotlin_file.relative_to(self.workspace_root)),
                            "type": "missing_kdoc",
                            "severity": "INFO",
                            "class": class_name,
                            "description": f"Class '{class_name}' lacks KDoc documentation"
                        })

            except Exception:
                pass

        return issues

    def check_security_patterns(self) -> List[Dict]:
        """Check for potential security issues."""
        issues = []

        security_patterns = [
            (r'Log\.[dv]\(.*password', "password_logging"),
            (r'Log\.[dv]\(.*token', "token_logging"),
            (r'http://', "insecure_http"),
            (r'TrustAllX509TrustManager', "trust_all_certs")
        ]

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if kotlin_file.exists():
                try:
                    content = kotlin_file.read_text(encoding='utf-8')

                    for pattern, issue_type in security_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": issue_type,
                                "severity": "WARNING",
                                "line": line_num,
                                "description": f"Potential security issue: {match.group()}"
                            })

                except Exception:
                    pass

        return issues

    def check_performance(self) -> List[Dict]:
        """Check for performance anti-patterns."""
        issues = []

        performance_patterns = [
            (r'findViewById\(', "findViewById_usage"),
            (r'\+\s*".*"\s*\+', "string_concatenation"),
            (r'for\s*\(.*in.*\)\s*{.*findViewById', "loop_findviewbyid")
        ]

        for kotlin_file in self.android_app_path.rglob("*.kt"):
            if kotlin_file.exists():
                try:
                    content = kotlin_file.read_text(encoding='utf-8')

                    for pattern, issue_type in performance_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            issues.append({
                                "file": str(kotlin_file.relative_to(self.workspace_root)),
                                "type": issue_type,
                                "severity": "INFO",
                                "line": line_num,
                                "description": f"Performance suggestion: {match.group()[:30]}..."
                            })

                except Exception:
                    pass

        return issues

    def print_report(self, results: Dict):
        """Print formatted quality report."""
        print("\n" + "="*60)
        print("🔍 CODE QUALITY ANALYSIS REPORT (INFO ONLY)")
        print("="*60)

        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"📊 Total Suggestions: {results['summary']['total_suggestions']}")

        for category, issues in results.items():
            if isinstance(issues, list) and issues:
                print(f"\n🔸 {category.replace('_', ' ').title()}:")
                for issue in issues[:3]:
                    severity_emoji = {"WARNING": "⚠️", "INFO": "💡"}.get(issue.get('severity', 'INFO'), "💡")
                    print(f"  {severity_emoji} {issue.get('description', 'No description')}")
                if len(issues) > 3:
                    print(f"  ... and {len(issues) - 3} more suggestions")

        print("\n💡 These are suggestions only - no automatic fixes applied per policy")
        print("="*60)

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        workspace_root = sys.argv[1]
    else:
        workspace_root = os.getcwd()

    checker = CodeQualityChecker(workspace_root)
    results = checker.check_quality()

    # Always exit 0 (info-only per policy)
    sys.exit(0)

if __name__ == "__main__":
    main()
