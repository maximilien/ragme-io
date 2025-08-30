#!/bin/bash

# RAGme Container Build Script using Podman
# This script builds all RAGme service containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    print_error "Podman is not installed. Please install podman first."
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/../.."

print_status "Building RAGme containers with Podman..."

# Build API service
print_status "Building API service container..."
podman build -f deployment/containers/Dockerfile.api -t ragme-api:latest .

# Build MCP service
print_status "Building MCP service container..."
podman build -f deployment/containers/Dockerfile.mcp -t ragme-mcp:latest .

# Build Agent service
print_status "Building Agent service container..."
podman build -f deployment/containers/Dockerfile.agent -t ragme-agent:latest .

# Build Frontend service
print_status "Building Frontend service container..."
podman build -f deployment/containers/Dockerfile.frontend -t ragme-frontend:latest .

print_status "All containers built successfully!"

# Display built images
print_status "Built images:"
podman images | grep ragme || print_warning "No ragme images found"

print_status "To test the containers locally, run:"
echo "  cd deployment/containers && podman-compose up"
echo ""
print_status "To push images to a registry, run:"
echo "  ./deployment/scripts/push-containers.sh <registry-url>"