"""
Run all tests for PuroBeach application.
This script runs all test modules and provides a summary.
"""

import sys
import os

# Change to project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

from test_database import test_database_tables, test_seed_data
from test_routes import test_public_routes, test_protected_routes
from test_templates import test_all_templates


def run_all_tests():
    """Run all test suites."""
    print("=" * 70)
    print("PUROBEACH - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    all_passed = True
    results = []

    # Database tests
    print("\n[1/3] DATABASE TESTS")
    print("-" * 70)
    try:
        test_database_tables()
        test_seed_data()
        print("[PASS] Database tests")
        results.append(("Database", True, None))
    except AssertionError as e:
        print(f"[FAIL] Database tests: {e}")
        results.append(("Database", False, str(e)))
        all_passed = False
    except Exception as e:
        print(f"[ERROR] Database tests: {e}")
        results.append(("Database", False, str(e)))
        all_passed = False

    # Route tests
    print("\n[2/3] ROUTE TESTS")
    print("-" * 70)
    try:
        test_public_routes()
        test_protected_routes()
        print("[PASS] Route tests")
        results.append(("Routes", True, None))
    except AssertionError as e:
        print(f"[FAIL] Route tests: {e}")
        results.append(("Routes", False, str(e)))
        all_passed = False
    except Exception as e:
        print(f"[ERROR] Route tests: {e}")
        results.append(("Routes", False, str(e)))
        all_passed = False

    # Template tests
    print("\n[3/3] TEMPLATE TESTS")
    print("-" * 70)
    try:
        test_all_templates()
        print("[PASS] Template tests")
        results.append(("Templates", True, None))
    except AssertionError as e:
        print(f"[FAIL] Template tests: {e}")
        results.append(("Templates", False, str(e)))
        all_passed = False
    except Exception as e:
        print(f"[ERROR] Template tests: {e}")
        results.append(("Templates", False, str(e)))
        all_passed = False

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    for name, success, error in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")
        if error:
            print(f"       Error: {error}")

    print("-" * 70)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")

    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[FAILED] Some tests failed")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
