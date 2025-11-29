#!/usr/bin/env python3
"""
Manual test script for environment detection.

This script tests the enhanced environment detection in various scenarios.
Run this to verify the implementation works correctly.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path to import mcpydoc
sys.path.insert(0, str(Path(__file__).parent))

from mcpydoc.env_detection import (
    get_active_python_environments,
    get_searched_directories,
    is_pipx_environment,
)


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 70 + "\n")


def test_basic_detection():
    """Test basic environment detection."""
    print("TEST 1: Basic Environment Detection")
    print("-" * 70)

    # Clear cache to get fresh results
    envs = get_active_python_environments(use_cache=False)

    print(f"\nFound {len(envs)} Python environment(s):")
    for i, env in enumerate(envs, 1):
        is_pipx = is_pipx_environment(env)
        marker = " [PIPX/UVX]" if is_pipx else ""
        print(f"  {i}. {env}{marker}")

    searched_dirs = get_searched_directories()
    if searched_dirs:
        print(
            f"\nSearched {len(searched_dirs)} directory(ies) for virtual environments:"
        )
        for i, directory in enumerate(searched_dirs, 1):
            print(f"  {i}. {directory}")

    return len(envs) > 0


def test_with_manual_override():
    """Test with MCPYDOC_PYTHON_PATH set."""
    print("TEST 2: Manual Override (MCPYDOC_PYTHON_PATH)")
    print("-" * 70)

    # Save original value
    original = os.environ.get("MCPYDOC_PYTHON_PATH")

    # Set to current directory
    test_path = str(Path.cwd())
    os.environ["MCPYDOC_PYTHON_PATH"] = test_path

    try:
        envs = get_active_python_environments(use_cache=False)

        if test_path in envs:
            print(f"✓ Manual override working: {test_path} is in results")
            success = True
        else:
            print(f"✗ Manual override failed: {test_path} not found in results")
            success = False
    finally:
        # Restore original value
        if original is not None:
            os.environ["MCPYDOC_PYTHON_PATH"] = original
        else:
            os.environ.pop("MCPYDOC_PYTHON_PATH", None)

    return success


def test_pipx_detection():
    """Test pipx/uvx environment detection."""
    print("TEST 3: pipx/uvx Detection")
    print("-" * 70)

    test_cases = [
        ("/home/user/.local/pipx/venvs/mcpydoc", True),
        ("/Users/user/.local/uvx/tool", True),
        ("/home/user/projects/myapp/.venv", False),
        ("/usr/local/lib/python3.12", False),
    ]

    all_passed = True
    for path, expected in test_cases:
        result = is_pipx_environment(path)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {path}: {result} (expected {expected})")
        if result != expected:
            all_passed = False

    return all_passed


def test_current_environment():
    """Test that current environment is detected."""
    print("TEST 4: Current Environment Detection")
    print("-" * 70)

    envs = get_active_python_environments(use_cache=False)
    current_env = sys.prefix

    # Normalize paths for comparison
    normalized_envs = [str(Path(e).resolve()) for e in envs]
    normalized_current = str(Path(current_env).resolve())

    if normalized_current in normalized_envs:
        print(f"✓ Current environment detected: {current_env}")
        return True
    else:
        print(f"✗ Current environment not detected: {current_env}")
        print(f"  Available environments: {envs}")
        return False


def main():
    """Run all tests."""
    print_separator()
    print("MCPyDoc Enhanced Environment Detection Test Suite")
    print_separator()

    results = []

    # Run tests
    results.append(("Basic Detection", test_basic_detection()))
    print_separator()

    results.append(("Manual Override", test_with_manual_override()))
    print_separator()

    results.append(("pipx/uvx Detection", test_pipx_detection()))
    print_separator()

    results.append(("Current Environment", test_current_environment()))
    print_separator()

    # Print summary
    print("TEST SUMMARY")
    print("-" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
