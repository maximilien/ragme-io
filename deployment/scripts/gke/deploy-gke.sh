#!/bin/bash

# RAGme GKE Deployment Script
# Deploys RAGme services to Google Kubernetes Engine (GKE)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}[GKE-DEPLOY]${NC} $1"
}

# Configuration
PROJECT_ID=${PROJECT_ID:-propane-atrium-471123-u4}
CLUSTER_NAME=${CLUSTER_NAME:-ragme-io}
ZONE=${ZONE:-us-central1}
REGISTRY=${REGISTRY:-gcr.io/${PROJECT_ID}}
IMAGE_TAG=${IMAGE_TAG:-latest}
NAMESPACE=${NAMESPACE:-ragme}

# Navigate to project root
cd "$(dirname "$0")"

# Function to show help
show_help() {
    echo -e "${BLUE}RAGme GKE Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  help      - Show this help message"
    echo "  setup     - Install required dependencies and configure gcloud"
    echo "  deploy    - Full deployment: build images, push to GCR, deploy services"
    echo "  build     - Build and push container images to GCR"
    echo "  apply     - Apply Kubernetes manifests only"
    echo "  destroy   - Delete all resources from GKE cluster"
    echo "  status    - Show deployment status"
    echo "  logs      - Show logs from all services"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID    - GCP Project ID (default: propane-atrium-471123-u4)"
    echo "  CLUSTER_NAME  - GKE Cluster name (default: ragme-io)"
    echo "  ZONE          - GCP Zone (default: us-central1)"
    echo "  REGISTRY      - Container registry (default: gcr.io/PROJECT_ID)"
    echo "  IMAGE_TAG     - Image tag (default: latest)"
    echo "  NAMESPACE     - Kubernetes namespace (default: ragme)"
    echo ""
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v gcloud &> /dev/null; then
        missing_deps+=("gcloud")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    fi
    
    if ! command -v podman &> /dev/null; then
        missing_deps+=("podman")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_status "Run '$0 setup' to install missing dependencies"
        exit 1
    fi
    
    print_status "All dependencies are available"
}

# Function to configure gcloud
configure_gcloud() {
    print_status "Configuring gcloud..."
    
    # Set project
    gcloud config set project ${PROJECT_ID}
    
    # Enable required APIs
    gcloud services enable container.googleapis.com
    gcloud services enable containerregistry.googleapis.com
    
    # Configure Docker for GCR
    gcloud auth configure-docker
    
    print_status "gcloud configured successfully"
}

# Function to get cluster credentials
get_cluster_credentials() {
    print_status "Getting cluster credentials..."
    
    gcloud container clusters get-credentials ${CLUSTER_NAME} \
        --zone ${ZONE} \
        --project ${PROJECT_ID}
    
    print_status "Cluster credentials configured"
}

# Function to create namespace
create_namespace() {
    print_status "Creating namespace: ${NAMESPACE}"
    
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    print_status "Namespace created/verified"
}

# Function to build and push images
build_and_push_images() {
    print_status "Building and pushing container images..."
    
    # Build images
    ./scripts/build-containers.sh
    
    # Tag and push images to GCR
    local images=("ragme-frontend" "ragme-api" "ragme-mcp" "ragme-agent")
    
    for image in "${images[@]}"; do
        print_status "Tagging and pushing ${image}..."
        
        # Tag for GCR
        podman tag localhost/${image}:${IMAGE_TAG} ${REGISTRY}/${image}:${IMAGE_TAG}
        
        # Push to GCR
        podman push ${REGISTRY}/${image}:${IMAGE_TAG}
        
        print_status "${image} pushed successfully"
    done
    
    print_status "All images built and pushed to GCR"
}

# Function to create ConfigMap and Secrets
create_config() {
    print_status "Creating ConfigMap and Secrets..."
    
    # Check if .env file exists
    if [ ! -f "../.env" ]; then
        print_error ".env file not found. Please create it from .env.example"
        exit 1
    fi
    
    # Check if config.yaml exists
    if [ ! -f "../config.yaml" ]; then
        print_error "config.yaml file not found. Please create it from config.yaml.example"
        exit 1
    fi
    
    # Create temporary ConfigMap file with individual keys
    local temp_configmap="/tmp/ragme-configmap-gke.yaml"
    
    cat > ${temp_configmap} << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ragme-config
  namespace: ${NAMESPACE}
data:
  # Application Configuration
  RAGME_API_PORT: "8021"
  RAGME_MCP_PORT: "8022"
  RAGME_FRONTEND_PORT: "8020"
  RAGME_API_URL: "http://ragme-api:8021"
  RAGME_MCP_URL: "http://ragme-mcp:8022"
  RAGME_UI_URL: "http://ragme-frontend:8020"
  
  # Vector Database Configuration
  VECTOR_DB_TYPE: "weaviate-local"
  VECTOR_DB_TEXT_COLLECTION_NAME: "ragme-text-collection"
  VECTOR_DB_IMAGE_COLLECTION_NAME: "ragme-image-collection"
  
  # MinIO Configuration
  MINIO_ENDPOINT: "ragme-minio:9000"
  
  # OAuth Redirect URIs
  GOOGLE_OAUTH_REDIRECT_URI: "http://localhost:8021/auth/google/callback"
  GITHUB_OAUTH_REDIRECT_URI: "http://localhost:8021/auth/github/callback"
  APPLE_OAUTH_REDIRECT_URI: "http://localhost:8021/auth/apple/callback"
EOF
    
    # Apply ConfigMap
    kubectl apply -f ${temp_configmap}
    
    # Create Secrets from .env file
    local temp_secrets="/tmp/ragme-secrets-gke.yaml"
    
    cat > ${temp_secrets} << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ragme-secrets
  namespace: ${NAMESPACE}
type: Opaque
data:
EOF
    
    # Add secrets from .env file
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ $key =~ ^[[:space:]]*# ]] || [[ -z $key ]]; then
            continue
        fi
        
        # Remove quotes and export prefix
        key=$(echo "$key" | sed 's/^export[[:space:]]*//' | tr -d '"')
        value=$(echo "$value" | tr -d '"')
        
        # Base64 encode the value
        encoded_value=$(echo -n "$value" | base64)
        
        echo "  ${key}: ${encoded_value}" >> ${temp_secrets}
    done < ../.env
    
    # Apply Secrets
    kubectl apply -f ${temp_secrets}
    
    # Clean up temp files
    rm -f ${temp_configmap} ${temp_secrets}
    
    print_status "ConfigMap and Secrets created"
}

# Function to update image references in manifests
update_manifests() {
    print_status "Updating image references in manifests..."
    
    # Create temporary directory for updated manifests
    local temp_dir="/tmp/ragme-manifests-gke"
    mkdir -p ${temp_dir}
    
    # Copy and update manifests
    for manifest in gke/k8s/*.yaml; do
        if [ -f "$manifest" ]; then
            local filename=$(basename "$manifest")
            local temp_manifest="${temp_dir}/${filename}"
            
            # Update image references
            sed "s|localhost/ragme-|${REGISTRY}/ragme-|g" "$manifest" > "$temp_manifest"
            sed -i "s|:latest|:${IMAGE_TAG}|g" "$temp_manifest"
            
            print_status "Updated ${filename}"
        fi
    done
    
    # Store temp directory path for later use
    echo "${temp_dir}" > /tmp/ragme-manifests-dir
}

# Function to apply Kubernetes manifests
apply_manifests() {
    print_status "Applying Kubernetes manifests using GKE-specific kustomization..."
    
    # Apply using kustomization for GKE
    kubectl apply -k gke/k8s/
    
    # Clean up temp directory
    if [ -d "/tmp/ragme-manifests-gke" ]; then
        rm -rf /tmp/ragme-manifests-gke
        rm -f /tmp/ragme-manifests-dir
    fi
    
    print_status "All manifests applied"
}

# Function to wait for deployments
wait_for_deployments() {
    print_status "Waiting for deployments to be ready..."
    
    local deployments=("ragme-weaviate" "ragme-minio" "ragme-api" "ragme-mcp" "ragme-agent" "ragme-frontend")
    
    for deployment in "${deployments[@]}"; do
        print_status "Waiting for ${deployment}..."
        kubectl wait --for=condition=available --timeout=300s deployment/${deployment} -n ${NAMESPACE} || {
            print_warning "${deployment} deployment may not be ready yet"
        }
    done
    
    print_status "Deployments are ready"
}

# Function to show status
show_status() {
    print_header "Deployment Status"
    
    echo ""
    print_status "Namespace:"
    kubectl get namespace ${NAMESPACE}
    
    echo ""
    print_status "Pods:"
    kubectl get pods -n ${NAMESPACE}
    
    echo ""
    print_status "Services:"
    kubectl get services -n ${NAMESPACE}
    
    echo ""
    print_status "Ingress:"
    kubectl get ingress -n ${NAMESPACE} 2>/dev/null || echo "No ingress found"
    
    echo ""
    print_status "External IPs:"
    kubectl get services -n ${NAMESPACE} -o wide | grep LoadBalancer || echo "No LoadBalancer services found"
}

# Function to show logs
show_logs() {
    print_header "Service Logs"
    
    local services=("ragme-frontend" "ragme-api" "ragme-mcp" "ragme-agent")
    
    for service in "${services[@]}"; do
        echo ""
        print_status "=== ${service} logs ==="
        kubectl logs -n ${NAMESPACE} -l app=${service} --tail=20 || echo "No logs found for ${service}"
    done
}

# Function to destroy deployment
destroy_deployment() {
    print_header "Destroying RAGme deployment"
    
    print_warning "This will delete all RAGme resources from the GKE cluster"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deleting namespace and all resources..."
        kubectl delete namespace ${NAMESPACE} --ignore-not-found=true
        
        print_status "Deployment destroyed"
    else
        print_status "Deployment destruction cancelled"
    fi
}

# Main script logic
main() {
    case "${1:-deploy}" in
        "help")
            show_help
            ;;
        "setup")
            check_dependencies
            configure_gcloud
            ;;
        "deploy")
            print_header "Starting RAGme GKE deployment"
            check_dependencies
            get_cluster_credentials
            create_namespace
            build_and_push_images
            create_config
            update_manifests
            apply_manifests
            wait_for_deployments
            show_status
            print_status "GKE deployment completed successfully!"
            ;;
        "build")
            print_header "Building and pushing images to GCR"
            check_dependencies
            build_and_push_images
            ;;
        "apply")
            print_header "Applying Kubernetes manifests"
            check_dependencies
            get_cluster_credentials
            create_namespace
            create_config
            update_manifests
            apply_manifests
            wait_for_deployments
            show_status
            ;;
        "config")
            print_header "Creating ConfigMap and Secrets"
            check_dependencies
            get_cluster_credentials
            create_namespace
            create_config
            print_status "ConfigMap and Secrets updated"
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "destroy")
            destroy_deployment
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
