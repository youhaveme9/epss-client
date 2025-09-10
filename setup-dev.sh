#!/bin/bash
# Development setup script for epss-client

set -e

echo "🚀 Setting up epss-client development environment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Run initial formatting
echo "🎨 Formatting code..."
black src/ tests/
isort src/ tests/

# Run linting
echo "🧹 Linting code..."
ruff check src/ tests/

# Run tests
echo "🧪 Running tests..."
pytest tests/ -v

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Available commands:"
echo "  make format      - Format code with black and isort"
echo "  make lint        - Lint code with ruff"
echo "  make lint-fix    - Fix linting issues automatically"
echo "  make test        - Run tests"
echo "  make check       - Run all checks (format, lint, test)"
echo "  make ci-check    - Run all CI checks locally"
echo ""
echo "🎉 Happy coding!"
