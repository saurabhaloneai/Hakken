#!/usr/bin/env python3
"""
Simple test runner for Hakken Agent tests

Usage:
    python tests/run_tests.py
    
This will run the core functionality tests to verify your agent works correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from test_agent_core_functionality import test_agent_core_functionality, test_realistic_coding_scenario


async def main():
    """Run all tests"""
    
    print("🚀 Hakken Agent Test Suite")
    print("=" * 40)
    print("Testing core functionality of your AI agent...")
    print()
    
    try:
        # Test 1: Core functionality
        print("🧪 Running Core Functionality Tests...")
        await test_agent_core_functionality()
        
        print("\n" + "-" * 40)
        
        # Test 2: Realistic scenario
        print("🧪 Running Realistic Scenario Tests...")
        await test_realistic_coding_scenario()
        
        print("\n" + "=" * 40)
        print("🎉 ALL TESTS PASSED!")
        print("✨ Your Hakken agent is working perfectly!")
        print("🚀 Ready for real-world coding tasks!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
