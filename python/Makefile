.PHONY: install install-dev test test-unit test-integration lint format type-check clean all

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
install-dev:
	pip install -e ".[dev]"

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest tests/test_sec_edgar_api.py -v

# Run integration tests only
test-integration:
	pytest tests/test_sec_edgar_api_integration.py -v

# Run linting with ruff
lint:
	ruff check src/ tests/

# Fix linting issues with ruff
lint-fix:
	ruff check src/ tests/ --fix

# Format code with black
format:
	black src/ tests/

# Run type checking with mypy
type-check:
	mypy src/

# Clean up generated files
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run all checks (lint, type-check, test)
all: lint type-check test

# Development workflow - format, lint, type-check, test
dev: format lint-fix type-check test