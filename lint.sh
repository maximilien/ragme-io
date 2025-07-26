#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

set -e

echo "🔍 Running Ruff linter on source and test files..."

# Run ruff check on all source, test, and example files
echo "📁 Checking source files..."
uv run ruff check src/

echo "🧪 Checking test files..."
uv run ruff check tests/

echo "📚 Checking example files..."
uv run ruff check examples/

echo "✅ All linting checks passed!"

# Optional: Run ruff format to check formatting
echo "🎨 Checking code formatting..."
uv run ruff format --check src/ tests/ examples/

echo "✨ All formatting checks passed!"
echo "🎯 Code quality checks completed successfully!" 