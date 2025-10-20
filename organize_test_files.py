#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Test File Organization Script
===============================================

File: organize_test_files.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Script to move all test files to tests/ folder and update imports

This script moves all test_*.py files to the tests/ directory and updates
their import statements to work from the new location.
"""

import os
import shutil
import re
from typing import List, Dict

class TestFileOrganizer:
    """Organizes test files into tests/ directory with proper imports."""
    
    def __init__(self, source_dir: str = ".", tests_dir: str = "tests"):
        self.source_dir = source_dir
        self.tests_dir = tests_dir
        self.moved_files = []
        
    def find_test_files(self) -> List[str]:
        """Find all test_*.py files in source directory."""
        test_files = []
        for file in os.listdir(self.source_dir):
            if file.startswith('test_') and file.endswith('.py'):
                # Skip if already in tests directory
                file_path = os.path.join(self.source_dir, file)
                if os.path.isfile(file_path):
                    test_files.append(file)
        return test_files
    
    def create_tests_directory(self):
        """Create tests directory if it doesn't exist."""
        if not os.path.exists(self.tests_dir):
            os.makedirs(self.tests_dir)
            print(f"✓ Created tests directory: {self.tests_dir}")
        
        # Create __init__.py file
        init_file = os.path.join(self.tests_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Test package for NFSP00F3R V5.0\\n')
            print("✓ Created __init__.py in tests directory")
    
    def update_imports_in_file(self, file_path: str) -> bool:
        """Update import statements in a file to work from tests/ directory."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Import patterns to update
            import_patterns = [
                # Direct imports from current directory
                (r'^(from\\s+)([a-zA-Z_][a-zA-Z0-9_]*)(\\s+import)', r'\\1..\\2\\3'),
                (r'^(import\\s+)([a-zA-Z_][a-zA-Z0-9_]*)', r'\\1..\\2'),
                
                # Relative imports that need parent directory
                (r'^(from\\s+)(?!\\.\\.)(\\w+)(\\s+import)', r'\\1..\\2\\3'),
                
                # Add parent directory for specific modules
                (r'from ui_mainwindow import', 'from ..ui_mainwindow import'),
                (r'from android_widget import', 'from ..android_widget import'),
                (r'from attack_panel import', 'from ..attack_panel import'),
                (r'from security_research_ui import', 'from ..security_research_ui import'),
                (r'from bluetooth_manager_ble import', 'from ..bluetooth_manager_ble import'),
                (r'from android_hce import', 'from ..android_hce import'),
                (r'from card_manager import', 'from ..card_manager import'),
                (r'from readers import', 'from ..readers import'),
                (r'from emv_card import', 'from ..emv_card import'),
                (r'from transaction import', 'from ..transaction import'),
                (r'from tlv import', 'from ..tlv import'),
                (r'from crypto import', 'from ..crypto import'),
                (r'from attack_manager import', 'from ..attack_manager import'),
                (r'from attack_modules import', 'from ..attack_modules import'),
                (r'from hardware_emulation import', 'from ..hardware_emulation import'),
                (r'from key_derivation_research_clean import', 'from ..key_derivation_research_clean import'),
                
                # Direct imports without from
                (r'^import ui_mainwindow$', 'import ..ui_mainwindow'),
                (r'^import android_widget$', 'import ..android_widget'),
                (r'^import attack_panel$', 'import ..attack_panel'),
                (r'^import card_manager$', 'import ..card_manager'),
                (r'^import emv_card$', 'import ..emv_card'),
                (r'^import tlv$', 'import ..tlv'),
                (r'^import crypto$', 'import ..crypto'),
            ]
            
            # Apply import fixes
            for pattern, replacement in import_patterns:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # Fix sys.path additions for parent directory access
            if 'sys.path.append' not in content and 'import sys' in content:
                # Add sys.path modification after import sys
                sys_import_pattern = r'(import sys\\n)'
                sys_replacement = r'\\1sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\\n'
                content = re.sub(sys_import_pattern, sys_replacement, content)
                
                # Make sure os is imported too
                if 'import os' not in content:
                    content = 'import os\\n' + content
            
            # Write updated content
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error updating imports in {file_path}: {e}")
            return False
    
    def move_test_file(self, filename: str) -> bool:
        """Move a test file to tests directory and update imports."""
        source_path = os.path.join(self.source_dir, filename)
        dest_path = os.path.join(self.tests_dir, filename)
        
        try:
            # Copy file to tests directory
            shutil.copy2(source_path, dest_path)
            
            # Update imports in the copied file
            imports_updated = self.update_imports_in_file(dest_path)
            
            # Remove original file
            os.remove(source_path)
            
            status = "with import updates" if imports_updated else "no import changes needed"
            print(f"✓ Moved {filename} to tests/ ({status})")
            
            self.moved_files.append(filename)
            return True
            
        except Exception as e:
            print(f"❌ Error moving {filename}: {e}")
            return False
    
    def organize_all_tests(self) -> Dict[str, List[str]]:
        """Organize all test files."""
        print("ORGANIZING TEST FILES")
        print("=" * 30)
        
        # Create tests directory
        self.create_tests_directory()
        
        # Find all test files
        test_files = self.find_test_files()
        print(f"\\nFound {len(test_files)} test files to move")
        
        # Move each test file
        successful_moves = []
        failed_moves = []
        
        for test_file in test_files:
            if self.move_test_file(test_file):
                successful_moves.append(test_file)
            else:
                failed_moves.append(test_file)
        
        # Create summary
        print(f"\\n📊 MOVE SUMMARY:")
        print(f"✓ Successfully moved: {len(successful_moves)} files")
        if failed_moves:
            print(f"❌ Failed to move: {len(failed_moves)} files")
            for failed_file in failed_moves:
                print(f"  - {failed_file}")
        
        return {
            'successful': successful_moves,
            'failed': failed_moves
        }
    
    def create_test_runner(self):
        """Create a test runner script in tests directory."""
        runner_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Test Runner
=============================

File: run_all_tests.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Run all tests in the tests directory

Usage: python run_all_tests.py
"""

import os
import sys
import unittest
import importlib.util

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def discover_and_run_tests():
    """Discover and run all tests in the tests directory."""
    print("NFSP00F3R V5.0 - Test Runner")
    print("=" * 40)
    
    # Discover tests in current directory
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - failures - errors}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\\n🎉 EXCELLENT - All tests passing!")
    elif success_rate >= 75:
        print("\\n✅ GOOD - Most tests passing")
    else:
        print("\\n⚠️  NEEDS ATTENTION - Many test failures")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = discover_and_run_tests()
    sys.exit(0 if success else 1)
'''
        
        runner_path = os.path.join(self.tests_dir, "run_all_tests.py")
        with open(runner_path, 'w', encoding='utf-8') as f:
            f.write(runner_content)
        
        print(f"✓ Created test runner: {runner_path}")

def main():
    """Main function to organize test files."""
    organizer = TestFileOrganizer()
    
    # Organize all test files
    results = organizer.organize_all_tests()
    
    # Create test runner
    organizer.create_test_runner()
    
    print("\\n🎉 TEST FILE ORGANIZATION COMPLETE!")
    print(f"All test files are now in the tests/ directory with updated imports.")
    print("Run tests with: python tests/run_all_tests.py")
    
    return len(results['failed']) == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
