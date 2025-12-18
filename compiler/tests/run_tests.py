#!/usr/bin/env python3
"""
Test Runner for Brainhair Compiler Tests

Discovers and runs all test_*.py files in the tests directory.
Reports pass/fail counts and exits with non-zero code on failure.
"""

import sys
import os
import importlib.util
from pathlib import Path

# Simple assertion framework
class TestFailure(Exception):
    """Exception raised when a test assertion fails"""
    pass

def assert_eq(actual, expected, message=""):
    """Assert that actual equals expected"""
    if actual != expected:
        error_msg = f"Assertion failed: {actual} != {expected}"
        if message:
            error_msg += f" ({message})"
        raise TestFailure(error_msg)

def assert_true(condition, message=""):
    """Assert that condition is true"""
    if not condition:
        error_msg = f"Assertion failed: expected True, got {condition}"
        if message:
            error_msg += f" ({message})"
        raise TestFailure(error_msg)

def assert_raises(exception_type, callable_func, message=""):
    """Assert that calling callable_func raises exception_type"""
    try:
        callable_func()
        error_msg = f"Assertion failed: expected {exception_type.__name__} to be raised"
        if message:
            error_msg += f" ({message})"
        raise TestFailure(error_msg)
    except exception_type:
        # Expected exception was raised
        pass
    except Exception as e:
        error_msg = f"Assertion failed: expected {exception_type.__name__}, got {type(e).__name__}"
        if message:
            error_msg += f" ({message})"
        raise TestFailure(error_msg)

# Make assertion functions globally available
globals()['assert_eq'] = assert_eq
globals()['assert_true'] = assert_true
globals()['assert_raises'] = assert_raises

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []

    def discover_tests(self, directory=None):
        """Discover all test_*.py files in the given directory"""
        if directory is None:
            directory = Path(__file__).parent

        test_files = sorted(directory.glob("test_*.py"))
        return test_files

    def load_module(self, file_path):
        """Load a Python module from a file path"""
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)

        # Add assertion functions to the module's namespace
        module.assert_eq = assert_eq
        module.assert_true = assert_true
        module.assert_raises = assert_raises

        spec.loader.exec_module(module)
        return module

    def run_test_function(self, module, func_name):
        """Run a single test function"""
        func = getattr(module, func_name)
        test_name = f"{module.__name__}.{func_name}"

        try:
            func()
            self.passed += 1
            self.test_results.append((test_name, "PASS", None))
            return True
        except TestFailure as e:
            self.failed += 1
            self.test_results.append((test_name, "FAIL", str(e)))
            return False
        except Exception as e:
            self.failed += 1
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.test_results.append((test_name, "ERROR", error_msg))
            return False

    def run_test_file(self, file_path):
        """Run all test functions in a file"""
        print(f"\n{'='*70}")
        print(f"Running tests from: {file_path.name}")
        print('='*70)

        try:
            module = self.load_module(file_path)
        except Exception as e:
            print(f"ERROR: Failed to load module: {e}")
            self.failed += 1
            return

        # Find all functions starting with 'test_'
        test_functions = [name for name in dir(module)
                         if name.startswith('test_') and callable(getattr(module, name))]

        if not test_functions:
            print("  No test functions found")
            return

        for func_name in test_functions:
            success = self.run_test_function(module, func_name)
            status = "PASS" if success else "FAIL"
            print(f"  [{status}] {func_name}")

    def run_all_tests(self, test_files=None):
        """Run all discovered tests"""
        if test_files is None:
            test_files = self.discover_tests()

        if not test_files:
            print("No test files found!")
            return

        print(f"Discovered {len(test_files)} test file(s)")

        for test_file in test_files:
            self.run_test_file(test_file)

        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        print(f"\n{'='*70}")
        print("TEST SUMMARY")
        print('='*70)

        # Print failures and errors
        if self.failed > 0:
            print("\nFailed tests:")
            for test_name, status, error in self.test_results:
                if status in ["FAIL", "ERROR"]:
                    print(f"\n  [{status}] {test_name}")
                    if error:
                        # Indent error messages
                        for line in error.split('\n'):
                            print(f"    {line}")

        # Print summary counts
        total = self.passed + self.failed
        print(f"\nTests run: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.failed == 0:
            print("\nAll tests passed!")
        else:
            print(f"\n{self.failed} test(s) failed")

def main():
    """Main entry point"""
    runner = TestRunner()

    # Check if specific test files were specified on command line
    if len(sys.argv) > 1:
        test_files = [Path(arg) for arg in sys.argv[1:]]
        # Validate files exist
        for f in test_files:
            if not f.exists():
                print(f"Error: Test file not found: {f}")
                sys.exit(1)
        runner.run_all_tests(test_files)
    else:
        # Run all discovered tests
        runner.run_all_tests()

    # Exit with non-zero code if any tests failed
    sys.exit(1 if runner.failed > 0 else 0)

if __name__ == '__main__':
    main()
