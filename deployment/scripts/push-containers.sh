#!/bin/bash

# RAGme Container Push Script using Podman
# This script tags and pushes all RAGme service containers to a registry

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

# Check if registry URL is provided
if [ $# -eq 0 ]; then
    print_error "Usage: $0 <registry-url> [tag]"
    echo "Examples:"
    echo "  $0 docker.io/myuser"
    echo "  $0 ghcr.io/myorg v1.0.0"
    echo "  $0 localhost:5000 latest"
    exit 1
fi

REGISTRY_URL=$1
TAG=${2:-latest}

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    print_error "Podman is not installed. Please install podman first."
    exit 1
fi

print_status "Pushing RAGme containers to $REGISTRY_URL with tag $TAG..."

# Services to push
SERVICES=("api" "mcp" "agent" "frontend")

for service in "${SERVICES[@]}"; do
    print_status "Tagging and pushing $service..."
    
    # Tag the image
    podman tag ragme-$service:latest $REGISTRY_URL/ragme-$service:$TAG
    
    # Push the image
    podman push $REGISTRY_URL/ragme-$service:$TAG
    
    print_status "$service pushed successfully!"
done

print_status "All containers pushed to $REGISTRY_URL!"

print_status "Images available at:"
for service in "${SERVICES[@]}"; do
    echo "  $REGISTRY_URL/ragme-$service:$TAG"
done