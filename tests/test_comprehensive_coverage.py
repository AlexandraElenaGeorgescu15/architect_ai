#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive coverage test runner
Runs all unit tests and generates coverage report
Target: 90%+ overall coverage for critical components
"""

import sys
import os
from pathlib import Path

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest


def run_comprehensive_tests():
    """Run all comprehensive unit tests"""
    print("=" * 70)
    print("ARCHITECT.AI - COMPREHENSIVE TEST SUITE")
    print("Target: 90%+ Coverage for Critical Components")
    print("=" * 70)
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        success_rate = 100.0
    else:
        failed = len(result.failures) + len(result.errors)
        success_rate = ((result.testsRun - failed) / result.testsRun) * 100
        print(f"\n⚠️ SOME TESTS FAILED - Success Rate: {success_rate:.1f}%")
    
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)


