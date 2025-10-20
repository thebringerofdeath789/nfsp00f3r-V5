#!/usr/bin/env python3
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
    print("\n" + "=" * 40)
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
        print("\n🎉 EXCELLENT - All tests passing!")
    elif success_rate >= 75:
        print("\n✅ GOOD - Most tests passing")
    else:
        print("\n⚠️  NEEDS ATTENTION - Many test failures")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = discover_and_run_tests()
    sys.exit(0 if success else 1)
