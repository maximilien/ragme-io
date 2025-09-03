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

# Function to check disk space
check_disk_space() {
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local required_space=5000000  # 5GB in KB
    if [ "$available_space" -lt "$required_space" ]; then
        print_warning "Low disk space detected. Available: ${available_space}KB"
        print_status "Cleaning up..."
        podman system prune -af || true
        sudo rm -rf /tmp/* || true
        sudo rm -rf /var/tmp/* || true
        available_space=$(df / | awk 'NR==2 {print $4}')
        print_status "Available space after cleanup: ${available_space}KB"
    fi
}

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    print_error "Podman is not installed. Please install podman first."
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/../.."

# Process config.yaml.example with environment variables
print_status "Processing config.yaml with environment variables..."
if [ -f ".env" ]; then
    # Load environment variables safely
    set -a
    source .env
    set +a
    
    # Create a processed config.yaml for the build using sed
    cp config.yaml.example config.yaml.processed
    
    # Replace environment variables in the config file
    if [ -n "$APPLICATION_NAME" ]; then
        sed -i.bak "s|\${APPLICATION_NAME}|$APPLICATION_NAME|g" config.yaml.processed
    fi
    if [ -n "$APPLICATION_VERSION" ]; then
        sed -i.bak "s|\${APPLICATION_VERSION}|$APPLICATION_VERSION|g" config.yaml.processed
    fi
    if [ -n "$APPLICATION_TITLE" ]; then
        sed -i.bak "s|\${APPLICATION_TITLE}|$APPLICATION_TITLE|g" config.yaml.processed
    fi
    if [ -n "$APPLICATION_DESCRIPTION" ]; then
        sed -i.bak "s|\${APPLICATION_DESCRIPTION}|$APPLICATION_DESCRIPTION|g" config.yaml.processed
    fi
    if [ -n "$OPENAI_API_KEY" ]; then
        sed -i.bak "s|\${OPENAI_API_KEY}|$OPENAI_API_KEY|g" config.yaml.processed
    fi
    if [ -n "$WEAVIATE_URL" ]; then
        sed -i.bak "s|\${WEAVIATE_URL}|$WEAVIATE_URL|g" config.yaml.processed
    fi
    if [ -n "$WEAVIATE_API_KEY" ]; then
        sed -i.bak "s|\${WEAVIATE_API_KEY}|$WEAVIATE_API_KEY|g" config.yaml.processed
    fi
    if [ -n "$VECTOR_DB_TYPE" ]; then
        sed -i.bak "s|\${VECTOR_DB_TYPE}|$VECTOR_DB_TYPE|g" config.yaml.processed
    fi
    if [ -n "$VECTOR_DB_TEXT_COLLECTION_NAME" ]; then
        sed -i.bak "s|\${VECTOR_DB_TEXT_COLLECTION_NAME}|$VECTOR_DB_TEXT_COLLECTION_NAME|g" config.yaml.processed
    fi
    if [ -n "$VECTOR_DB_IMAGE_COLLECTION_NAME" ]; then
        sed -i.bak "s|\${VECTOR_DB_IMAGE_COLLECTION_NAME}|$VECTOR_DB_IMAGE_COLLECTION_NAME|g" config.yaml.processed
    fi
    if [ -n "$MILVUS_URI" ]; then
        sed -i.bak "s|\${MILVUS_URI}|$MILVUS_URI|g" config.yaml.processed
    fi
    if [ -n "$MILVUS_TOKEN" ]; then
        sed -i.bak "s|\${MILVUS_TOKEN}|$MILVUS_TOKEN|g" config.yaml.processed
    fi
    if [ -n "$WATCH_DIRECTORY" ]; then
        sed -i.bak "s|\${WATCH_DIRECTORY}|$WATCH_DIRECTORY|g" config.yaml.processed
    fi
    if [ -n "$MINIO_LOCAL_PATH" ]; then
        sed -i.bak "s|\${MINIO_LOCAL_PATH}|$MINIO_LOCAL_PATH|g" config.yaml.processed
    fi
    
    # Clean up backup files
    rm -f config.yaml.processed.bak
    
    print_status "Config processed with environment variables"
else
    print_warning "No .env file found, using config.yaml.example as-is"
    cp config.yaml.example config.yaml.processed
fi

print_status "Building RAGme containers with Podman..."

# Check disk space before building
check_disk_space

# Build API service
print_status "Building API service container..."
podman build -f deployment/containers/Dockerfile.api -t localhost/ragme-api:latest .
check_disk_space

# Build MCP service
print_status "Building MCP service container..."
podman build -f deployment/containers/Dockerfile.mcp -t localhost/ragme-mcp:latest .
check_disk_space

# Build Agent service
print_status "Building Agent service container..."
podman build -f deployment/containers/Dockerfile.agent -t localhost/ragme-agent:latest .
check_disk_space

# Build Frontend service
print_status "Building Frontend service container..."
podman build -f deployment/containers/Dockerfile.frontend -t localhost/ragme-frontend:latest .

print_status "All containers built successfully!"

# Clean up processed config file
rm -f config.yaml.processed

# Display built images
print_status "Built images:"
podman images | grep ragme || print_warning "No ragme images found"

print_status "To test the containers locally, run:"
echo "  cd deployment/containers && podman-compose up"
echo ""
print_status "To push images to a registry, run:"
echo "  ./deployment/scripts/push-containers.sh <registry-url>"