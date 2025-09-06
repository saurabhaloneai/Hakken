"""Pytest configuration and fixtures for Hakken tests"""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing"""
    file_path = temp_dir / "sample.py"
    content = '''class TestClass:
    def test_method(self):
        return "hello world"
        
def function_example():
    print("test function")
'''
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure for testing"""
    # Create directories
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()
    
    # Create Python files
    (temp_dir / "src" / "__init__.py").write_text("")
    (temp_dir / "src" / "main.py").write_text('''
def main():
    print("Hello from main")
    
class MainClass:
    pass
''')
    
    (temp_dir / "tests" / "test_main.py").write_text('''
import unittest

class TestMain(unittest.TestCase):
    def test_example(self):
        assert True
''')
    
    # Create other files
    (temp_dir / "README.md").write_text("# Test Project\n\nThis is a test.")
    (temp_dir / "requirements.txt").write_text("pytest\nrequests")
    
    return temp_dir
