# Makefile

# Makefile for managing the Hakken project

.PHONY: install lint test clean

# Install dependencies
install:
    pip install -r requirements.txt

# Run linters
lint:
    flake8 src tests

# Run tests
test:
    pytest tests

# Clean up __pycache__ directories
clean:
    find . -type d -name '__pycache__' -exec rm -r {} +