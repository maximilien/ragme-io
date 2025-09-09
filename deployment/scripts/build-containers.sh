#!/bin/bash

# RAGme Container Build Script using Podman
# This script builds all RAGme service containers with platform-specific options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PLATFORM=""
TARGET=""
REGISTRY="localhost:5001"
IMAGE_TAG="latest"
NO_CACHE=""
SERVICE=""

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

print_header() {
    echo -e "${BLUE}[BUILD]${NC} $1"
}

# Function to show help
show_help() {
    echo -e "${BLUE}RAGme Container Build Script${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --target TARGET     Build target: kind, gke, local (default: auto-detect)"
    echo "  -p, --platform PLATFORM Build platform: linux/amd64, linux/arm64 (default: auto-detect)"
    echo "  -r, --registry REGISTRY Container registry (default: localhost:5001)"
    echo "  --tag TAG               Image tag (default: latest)"
    echo "  -s, --service SERVICE   Build only specific service: frontend, api, mcp, agent (default: all)"
    echo "  --no-cache              Build without using cache"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --target kind                    # Build for kind (local development)"
    echo "  $0 --target gke                     # Build for GKE (linux/amd64)"
    echo "  $0 --platform linux/amd64          # Force AMD64 platform"
    echo "  $0 --target gke --registry gcr.io/project-id  # Build for GKE with custom registry"
    echo "  $0 --service frontend               # Build only frontend service"
    echo "  $0 --service api --no-cache         # Build only API service without cache"
    echo ""
    echo "Auto-detection:"
    echo "  - If no target specified, detects based on kubectl context"
    echo "  - If no platform specified, detects based on target and host OS"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate service argument if provided
if [ -n "$SERVICE" ]; then
    case "$SERVICE" in
        frontend|api|mcp|agent)
            print_status "Building only $SERVICE service"
            ;;
        *)
            print_error "Invalid service: $SERVICE. Valid options: frontend, api, mcp, agent"
            exit 1
            ;;
    esac
fi

# Auto-detect target if not specified
if [ -z "$TARGET" ]; then
    if command -v kubectl &> /dev/null; then
        CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "")
        if [[ "$CURRENT_CONTEXT" == *"kind"* ]]; then
            TARGET="kind"
        elif [[ "$CURRENT_CONTEXT" == *"gke"* ]]; then
            TARGET="gke"
        else
            TARGET="local"
        fi
    else
        TARGET="local"
    fi
    print_status "Auto-detected target: $TARGET"
fi

# Auto-detect platform if not specified
if [ -z "$PLATFORM" ]; then
    case "$TARGET" in
        "gke")
            PLATFORM="linux/amd64"
            ;;
        "kind")
            # Detect host architecture for kind
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS - check if Apple Silicon or Intel
                if [[ $(uname -m) == "arm64" ]]; then
                    PLATFORM="linux/arm64"
                else
                    PLATFORM="linux/amd64"
                fi
            else
                # Linux - use host architecture
                PLATFORM="linux/$(uname -m)"
            fi
            ;;
        "local")
            # Use host architecture for local builds
            if [[ "$OSTYPE" == "darwin"* ]]; then
                if [[ $(uname -m) == "arm64" ]]; then
                    PLATFORM="linux/arm64"
                else
                    PLATFORM="linux/amd64"
                fi
            else
                PLATFORM="linux/$(uname -m)"
            fi
            ;;
        *)
            PLATFORM="linux/amd64"
            ;;
    esac
    print_status "Auto-detected platform: $PLATFORM"
fi

print_header "Building RAGme containers for $TARGET target on $PLATFORM platform"

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
    # Use config.yaml if available, otherwise fall back to config.yaml.example
    if [ -f "config.yaml" ]; then
        cp config.yaml config.yaml.processed
    elif [ -f "config.yaml.example" ]; then
        cp config.yaml.example config.yaml.processed
        print_warning "Using config.yaml.example as config.yaml is not available"
    else
        print_error "Neither config.yaml nor config.yaml.example found!"
        exit 1
    fi
    
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
    
    # OAuth Configuration
    if [ -n "$GOOGLE_OAUTH_CLIENT_ID" ]; then
        sed -i.bak "s|\${GOOGLE_OAUTH_CLIENT_ID}|$GOOGLE_OAUTH_CLIENT_ID|g" config.yaml.processed
    fi
    if [ -n "$GOOGLE_OAUTH_CLIENT_SECRET" ]; then
        sed -i.bak "s|\${GOOGLE_OAUTH_CLIENT_SECRET}|$GOOGLE_OAUTH_CLIENT_SECRET|g" config.yaml.processed
    fi
    if [ -n "$GOOGLE_OAUTH_REDIRECT_URI" ]; then
        sed -i.bak "s|\${GOOGLE_OAUTH_REDIRECT_URI}|$GOOGLE_OAUTH_REDIRECT_URI|g" config.yaml.processed
    fi
    if [ -n "$GITHUB_OAUTH_CLIENT_ID" ]; then
        sed -i.bak "s|\${GITHUB_OAUTH_CLIENT_ID}|$GITHUB_OAUTH_CLIENT_ID|g" config.yaml.processed
    fi
    if [ -n "$GITHUB_OAUTH_CLIENT_SECRET" ]; then
        sed -i.bak "s|\${GITHUB_OAUTH_CLIENT_SECRET}|$GITHUB_OAUTH_CLIENT_SECRET|g" config.yaml.processed
    fi
    if [ -n "$GITHUB_OAUTH_REDIRECT_URI" ]; then
        sed -i.bak "s|\${GITHUB_OAUTH_REDIRECT_URI}|$GITHUB_OAUTH_REDIRECT_URI|g" config.yaml.processed
    fi
    if [ -n "$APPLE_OAUTH_CLIENT_ID" ]; then
        sed -i.bak "s|\${APPLE_OAUTH_CLIENT_ID}|$APPLE_OAUTH_CLIENT_ID|g" config.yaml.processed
    fi
    if [ -n "$APPLE_OAUTH_CLIENT_SECRET" ]; then
        sed -i.bak "s|\${APPLE_OAUTH_CLIENT_SECRET}|$APPLE_OAUTH_CLIENT_SECRET|g" config.yaml.processed
    fi
    if [ -n "$APPLE_OAUTH_REDIRECT_URI" ]; then
        sed -i.bak "s|\${APPLE_OAUTH_REDIRECT_URI}|$APPLE_OAUTH_REDIRECT_URI|g" config.yaml.processed
    fi
    if [ -n "$SESSION_SECRET_KEY" ]; then
        sed -i.bak "s|\${SESSION_SECRET_KEY}|$SESSION_SECRET_KEY|g" config.yaml.processed
    fi
    
    # Update CSP configuration for Kubernetes NodePort deployment
    # Replace localhost:8021 with localhost:30021 (API NodePort)
    # Replace localhost:8020 with localhost:30020 (Frontend NodePort)
    sed -i.bak "s|http://localhost:8021|http://localhost:30021|g" config.yaml.processed
    sed -i.bak "s|ws://localhost:8021|ws://localhost:30021|g" config.yaml.processed
    sed -i.bak "s|http://localhost:8020|http://localhost:30020|g" config.yaml.processed
    sed -i.bak "s|ws://localhost:8020|ws://localhost:30020|g" config.yaml.processed
    
    # Update environment variables for Kubernetes NodePort deployment
    # Set RAGME_API_URL to external NodePort URL for frontend server
    export RAGME_API_URL="http://ragme-api:8021"
    export RAGME_MCP_URL="http://ragme-mcp:8022"
    export RAGME_UI_URL="http://localhost:30020"
    
    # Substitute environment variables in config.yaml.processed
    if [ -n "$RAGME_API_URL" ]; then
        sed -i.bak "s|\${RAGME_API_URL}|$RAGME_API_URL|g" config.yaml.processed
    fi
    if [ -n "$RAGME_MCP_URL" ]; then
        sed -i.bak "s|\${RAGME_MCP_URL}|$RAGME_MCP_URL|g" config.yaml.processed
    fi
    if [ -n "$RAGME_UI_URL" ]; then
        sed -i.bak "s|\${RAGME_UI_URL}|$RAGME_UI_URL|g" config.yaml.processed
    fi
    
    # Weaviate Configuration - use values from .env file as-is
    if [ -n "$WEAVIATE_URL" ]; then
        sed -i.bak "s|\${WEAVIATE_URL}|$WEAVIATE_URL|g" config.yaml.processed
    fi
    if [ -n "$WEAVIATE_API_KEY" ]; then
        sed -i.bak "s|\${WEAVIATE_API_KEY}|$WEAVIATE_API_KEY|g" config.yaml.processed
    fi
    
    # Vector Database Collection Names
    if [ -n "$VECTOR_DB_TEXT_COLLECTION_NAME" ]; then
        sed -i.bak "s|\${VECTOR_DB_TEXT_COLLECTION_NAME}|$VECTOR_DB_TEXT_COLLECTION_NAME|g" config.yaml.processed
    fi
    if [ -n "$VECTOR_DB_IMAGE_COLLECTION_NAME" ]; then
        sed -i.bak "s|\${VECTOR_DB_IMAGE_COLLECTION_NAME}|$VECTOR_DB_IMAGE_COLLECTION_NAME|g" config.yaml.processed
    fi
    
    # Clean up backup files
    rm -f config.yaml.processed.bak
    
    print_status "Config processed with environment variables"
else
    print_warning "No .env file found, using config.yaml as-is"
    # Use config.yaml if available, otherwise fall back to config.yaml.example
    if [ -f "config.yaml" ]; then
        cp config.yaml config.yaml.processed
    elif [ -f "config.yaml.example" ]; then
        cp config.yaml.example config.yaml.processed
        print_warning "Using config.yaml.example as config.yaml is not available"
    else
        print_error "Neither config.yaml nor config.yaml.example found!"
        exit 1
    fi
    
    # Update CSP configuration for Kubernetes NodePort deployment even without .env
    # Replace localhost:8021 with localhost:30021 (API NodePort)
    # Replace localhost:8020 with localhost:30020 (Frontend NodePort)
    sed -i.bak "s|http://localhost:8021|http://localhost:30021|g" config.yaml.processed
    sed -i.bak "s|ws://localhost:8021|ws://localhost:30021|g" config.yaml.processed
    sed -i.bak "s|http://localhost:8020|http://localhost:30020|g" config.yaml.processed
    sed -i.bak "s|ws://localhost:8020|ws://localhost:30020|g" config.yaml.processed
    
    # Update environment variables for Kubernetes NodePort deployment
    # Set RAGME_API_URL to external NodePort URL for frontend server
    export RAGME_API_URL="http://ragme-api:8021"
    export RAGME_MCP_URL="http://ragme-mcp:8022"
    export RAGME_UI_URL="http://localhost:30020"
    
    # Substitute environment variables in config.yaml.processed
    if [ -n "$RAGME_API_URL" ]; then
        sed -i.bak "s|\${RAGME_API_URL}|$RAGME_API_URL|g" config.yaml.processed
    fi
    if [ -n "$RAGME_MCP_URL" ]; then
        sed -i.bak "s|\${RAGME_MCP_URL}|$RAGME_MCP_URL|g" config.yaml.processed
    fi
    if [ -n "$RAGME_UI_URL" ]; then
        sed -i.bak "s|\${RAGME_UI_URL}|$RAGME_UI_URL|g" config.yaml.processed
    fi
    
    # Weaviate Configuration - use values from .env file as-is
    if [ -n "$WEAVIATE_URL" ]; then
        sed -i.bak "s|\${WEAVIATE_URL}|$WEAVIATE_URL|g" config.yaml.processed
    fi
    if [ -n "$WEAVIATE_API_KEY" ]; then
        sed -i.bak "s|\${WEAVIATE_API_KEY}|$WEAVIATE_API_KEY|g" config.yaml.processed
    fi
    
    # Vector Database Collection Names
    if [ -n "$VECTOR_DB_TEXT_COLLECTION_NAME" ]; then
        sed -i.bak "s|\${VECTOR_DB_TEXT_COLLECTION_NAME}|$VECTOR_DB_TEXT_COLLECTION_NAME|g" config.yaml.processed
    fi
    if [ -n "$VECTOR_DB_IMAGE_COLLECTION_NAME" ]; then
        sed -i.bak "s|\${VECTOR_DB_IMAGE_COLLECTION_NAME}|$VECTOR_DB_IMAGE_COLLECTION_NAME|g" config.yaml.processed
    fi
    
    # Clean up backup files
    rm -f config.yaml.processed.bak
fi

# Set image names based on target
if [ "$TARGET" = "gke" ]; then
    # For GKE, use GCR registry format
    API_IMAGE="$REGISTRY/ragme-api:$IMAGE_TAG"
    MCP_IMAGE="$REGISTRY/ragme-mcp:$IMAGE_TAG"
    AGENT_IMAGE="$REGISTRY/ragme-agent:$IMAGE_TAG"
    FRONTEND_IMAGE="$REGISTRY/ragme-frontend:$IMAGE_TAG"
else
    # For kind/local, use localhost format
    API_IMAGE="localhost/ragme-api:$IMAGE_TAG"
    MCP_IMAGE="localhost/ragme-mcp:$IMAGE_TAG"
    AGENT_IMAGE="localhost/ragme-agent:$IMAGE_TAG"
    FRONTEND_IMAGE="localhost/ragme-frontend:$IMAGE_TAG"
fi

print_status "Building RAGme containers with Podman..."
print_status "Platform: $PLATFORM"
print_status "Target: $TARGET"
print_status "Registry: $REGISTRY"

# Check disk space before building
check_disk_space

# Build services based on selection
if [ -z "$SERVICE" ] || [ "$SERVICE" = "api" ]; then
    print_status "Building API service container..."
    podman build $NO_CACHE --platform "$PLATFORM" -f deployment/containers/Dockerfile.api -t "$API_IMAGE" .
    check_disk_space
fi

if [ -z "$SERVICE" ] || [ "$SERVICE" = "mcp" ]; then
    print_status "Building MCP service container..."
    podman build $NO_CACHE --platform "$PLATFORM" -f deployment/containers/Dockerfile.mcp -t "$MCP_IMAGE" .
    check_disk_space
fi

if [ -z "$SERVICE" ] || [ "$SERVICE" = "agent" ]; then
    print_status "Building Agent service container..."
    podman build $NO_CACHE --platform "$PLATFORM" -f deployment/containers/Dockerfile.agent -t "$AGENT_IMAGE" .
    check_disk_space
fi

if [ -z "$SERVICE" ] || [ "$SERVICE" = "frontend" ]; then
    print_status "Building Frontend service container..."
    podman build $NO_CACHE \
      --platform "$PLATFORM" \
      --build-arg RAGME_API_URL="$RAGME_API_URL" \
      --build-arg RAGME_MCP_URL="$RAGME_MCP_URL" \
      --build-arg RAGME_UI_URL="$RAGME_UI_URL" \
      -f deployment/containers/Dockerfile.frontend \
      -t "$FRONTEND_IMAGE" .
fi

if [ -n "$SERVICE" ]; then
    print_status "$SERVICE service built successfully!"
else
    print_status "All containers built successfully!"
fi

# Clean up processed config file
rm -f config.yaml.processed

# Display built images
print_status "Built images:"
podman images | grep ragme || print_warning "No ragme images found"

# Push images if target is GKE
if [ "$TARGET" = "gke" ]; then
    print_status "Pushing images to GCR registry..."
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker --quiet
    
    # Push each image
    print_status "Pushing API image..."
    podman push "$API_IMAGE"
    
    print_status "Pushing MCP image..."
    podman push "$MCP_IMAGE"
    
    print_status "Pushing Agent image..."
    podman push "$AGENT_IMAGE"
    
    print_status "Pushing Frontend image..."
    podman push "$FRONTEND_IMAGE"
    
    print_status "All images pushed to GCR successfully!"
    print_status "Images are now available at:"
    echo "  - $API_IMAGE"
    echo "  - $MCP_IMAGE"
    echo "  - $AGENT_IMAGE"
    echo "  - $FRONTEND_IMAGE"
else
    print_status "For kind deployment, images are ready locally"
    print_status "To test the containers locally, run:"
    echo "  cd deployment/containers && podman-compose up"
fi