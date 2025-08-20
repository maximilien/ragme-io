#!/bin/bash

# RAGme.io CI/CD Setup Script
# Non-interactive setup script for CI/CD environments

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[CI-SETUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[CI-SETUP]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[CI-SETUP]${NC} $1"
}

print_header "Starting RAGme.io CI Setup..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Python dependencies
print_header "Setting up Python dependencies..."

# Check if uv is installed
if ! command_exists uv; then
    print_status "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
uv sync

# Install test dependencies
print_status "Installing test dependencies..."
uv pip install -r requirements-test.txt

# Install development tools
print_status "Installing development tools..."
uv pip install ruff

# Install Node.js dependencies
print_header "Setting up Node.js dependencies..."

cd frontend

# Install dependencies
print_status "Installing Node.js dependencies..."
npm ci --silent

# Test build
print_status "Testing TypeScript compilation..."
npm run build --silent

cd ..

# Run basic tests
print_header "Running basic tests..."

# Test Python setup
print_status "Testing Python setup..."
uv run --active python -c "import sys; print(f'Python {sys.version}')"

# Test Node.js setup
print_status "Testing Node.js setup..."
cd frontend && npm run build --silent && cd ..

# Run unit tests
print_status "Running unit tests..."
./test.sh unit

print_header "CI Setup Complete! ✅"
print_status "All dependencies installed and tests passing"
