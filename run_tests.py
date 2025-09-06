#!/usr/bin/env python3
"""
Simple test runner for Hakken
"""
import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Run all tests with pytest"""
    print("🧪 Running Hakken Tests")
    print("=" * 40)
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add src to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Check if pytest is available
    try:
        import pytest
        print("✅ pytest found")
    except ImportError:
        print("❌ pytest not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"])
        import pytest
    
    # Run tests
    print("\n🚀 Running tests...")
    
    # Test arguments
    test_args = [
        "tests/",
        "-v",  # verbose
        "--tb=short",  # shorter traceback format
        "-x",  # stop on first failure
    ]
    
    try:
        exit_code = pytest.main(test_args)
        
        if exit_code == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n❌ Tests failed with exit code {exit_code}")
            
        return exit_code
        
    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        return 1


def run_specific_test(test_path):
    """Run a specific test file or test"""
    print(f"🧪 Running specific test: {test_path}")
    print("=" * 40)
    
    try:
        import pytest
        exit_code = pytest.main([test_path, "-v"])
        return exit_code
    except Exception as e:
        print(f"💥 Error running test: {e}")
        return 1


def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        exit_code = run_specific_test(test_path)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
