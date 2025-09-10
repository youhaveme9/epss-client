.PHONY: install install-dev test format lint check clean help

# Variables
PYTHON := python3
PIP := pip
SRC_DIR := src
TEST_DIR := tests

help:	## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:	## Install the package
	$(PIP) install -e .

install-dev:	## Install development dependencies
	$(PIP) install -e ".[dev]"

test:	## Run tests
	$(PYTHON) -m pytest $(TEST_DIR)/ -v

test-coverage:	## Run tests with coverage
	$(PYTHON) -m pytest $(TEST_DIR)/ -v --cov=$(SRC_DIR)/epss_client --cov-report=term-missing --cov-report=html

format:	## Format code with black and isort
	$(PYTHON) -m black $(SRC_DIR)/ $(TEST_DIR)/
	$(PYTHON) -m isort $(SRC_DIR)/ $(TEST_DIR)/

lint:	## Lint code with ruff
	$(PYTHON) -m ruff check $(SRC_DIR)/ $(TEST_DIR)/

lint-fix:	## Lint and fix code with ruff
	$(PYTHON) -m ruff check --fix $(SRC_DIR)/ $(TEST_DIR)/

check:	## Run all checks (format, lint, test)
	@echo "Running code formatting checks..."
	$(PYTHON) -m black --check $(SRC_DIR)/ $(TEST_DIR)/
	$(PYTHON) -m isort --check-only $(SRC_DIR)/ $(TEST_DIR)/
	@echo "Running linting..."
	$(PYTHON) -m ruff check $(SRC_DIR)/ $(TEST_DIR)/
	@echo "Running tests..."
	$(PYTHON) -m pytest $(TEST_DIR)/ -v

format-check:	## Check if code is properly formatted
	$(PYTHON) -m black --check $(SRC_DIR)/ $(TEST_DIR)/
	$(PYTHON) -m isort --check-only $(SRC_DIR)/ $(TEST_DIR)/

clean:	## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:	## Build the package
	$(PYTHON) -m build

pre-commit-install:	## Install pre-commit hooks
	$(PYTHON) -m pre_commit install

pre-commit-run:	## Run pre-commit on all files
	$(PYTHON) -m pre_commit run --all-files

ci-check:	## Run all CI checks locally
	@echo "=== Running CI checks locally ==="
	@echo "1. Code formatting check..."
	@$(PYTHON) -m black --check $(SRC_DIR)/ $(TEST_DIR)/ || (echo "❌ Code formatting check failed" && exit 1)
	@$(PYTHON) -m isort --check-only $(SRC_DIR)/ $(TEST_DIR)/ || (echo "❌ Import sorting check failed" && exit 1)
	@echo "✅ Code formatting check passed"
	@echo "2. Linting..."
	@$(PYTHON) -m ruff check $(SRC_DIR)/ $(TEST_DIR)/ || (echo "❌ Linting failed" && exit 1)
	@echo "✅ Linting passed"
	@echo "3. Running tests..."
	@$(PYTHON) -m pytest $(TEST_DIR)/ -v || (echo "❌ Tests failed" && exit 1)
	@echo "✅ Tests passed"
	@echo "🎉 All CI checks passed!"
