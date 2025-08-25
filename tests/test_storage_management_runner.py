#!/usr/bin/env python3
"""
Test runner for storage management tool tests
"""

import os
import subprocess
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def run_unit_tests():
    """Run unit tests for storage management"""
    print("🧪 Running Storage Management Unit Tests...")
    print("=" * 50)

    test_file = project_root / "tests" / "test_storage_management.py"

    if not test_file.exists():
        print(f"❌ Unit test file not found: {test_file}")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0


def run_integration_tests():
    """Run integration tests for storage management"""
    print("\n🔗 Running Storage Management Integration Tests...")
    print("=" * 50)

    test_file = (
        project_root
        / "tests"
        / "integration"
        / "test_storage_management_integration.py"
    )

    if not test_file.exists():
        print(f"❌ Integration test file not found: {test_file}")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0


def run_cli_tests():
    """Run CLI command tests"""
    print("\n🖥️  Running Storage Management CLI Tests...")
    print("=" * 50)

    # Test basic CLI commands
    commands = [
        ["help"],
        ["info"],
        ["health"],
        ["buckets"],
        ["list"],
        ["list", "--all"],
        ["links"],
    ]

    all_passed = True

    for cmd in commands:
        print(f"Testing: ./tools/storage.sh {' '.join(cmd)}")
        result = subprocess.run(
            ["./tools/storage.sh"] + cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode == 0:
            print(f"✅ Command {' '.join(cmd)} passed")
        else:
            print(f"❌ Command {' '.join(cmd)} failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            all_passed = False

    return all_passed


def main():
    """Main test runner"""
    print("🚀 Storage Management Tool Test Suite")
    print("=" * 50)

    # Check if we're in the right directory
    if not (project_root / "config.yaml").exists():
        print("❌ Error: config.yaml not found. Please run from project root.")
        sys.exit(1)

    # Check if storage script exists
    storage_script = project_root / "tools" / "storage.sh"
    if not storage_script.exists():
        print("❌ Error: tools/storage.sh not found.")
        sys.exit(1)

    # Make sure storage script is executable
    if not os.access(storage_script, os.X_OK):
        print("⚠️  Making storage script executable...")
        os.chmod(storage_script, 0o755)

    # Run tests
    unit_passed = run_unit_tests()
    integration_passed = run_integration_tests()
    cli_passed = run_cli_tests()

    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    print(f"Unit Tests: {'✅ PASSED' if unit_passed else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    print(f"CLI Tests: {'✅ PASSED' if cli_passed else '❌ FAILED'}")

    if unit_passed and integration_passed and cli_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
