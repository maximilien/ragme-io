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
cd "$(dirname "$0")/../.."

# Function to show help
show_help() {
    echo -e "${BLUE}RAGme GKE Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  help      - Show this help message"
    echo "  setup     - Install required dependencies and configure gcloud"
    echo "  list      - List available GKE clusters"
    echo "  create    - Create a new GKE cluster"
    echo "  deploy    - Full deployment: build images, push to GCR, deploy services"
    echo "  build     - Build and push container images to GCR"
    echo "  apply     - Apply Kubernetes manifests only"
    echo "  destroy   - Delete all resources from GKE cluster"
    echo "  cleanup-secrets - Clean up secrets from configmap-gke.yaml file"
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

# Function to list available clusters
list_clusters() {
    print_status "Available GKE clusters in project ${PROJECT_ID}:"
    echo ""
    
    local clusters=$(gcloud container clusters list --format="table(name,location,masterVersion,status)" --filter="status:RUNNING")
    
    if [ -z "$clusters" ]; then
        print_warning "No running clusters found in project ${PROJECT_ID}"
        echo ""
        print_status "Would you like to create a new cluster? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            create_cluster
        else
            print_error "No cluster available. Exiting."
            exit 1
        fi
    else
        echo "$clusters"
        echo ""
        print_status "Current cluster configuration:"
        print_status "  CLUSTER_NAME: ${CLUSTER_NAME}"
        print_status "  ZONE: ${ZONE}"
        echo ""
        print_status "To use a different cluster, set CLUSTER_NAME and ZONE environment variables:"
        print_status "  CLUSTER_NAME=your-cluster-name ZONE=your-zone $0 deploy"
    fi
}

# Function to create a new cluster
create_cluster() {
    print_status "Creating new GKE cluster..."
    
    local cluster_name=${CLUSTER_NAME:-ragme-io}
    local zone=${ZONE:-us-central1-a}
    local machine_type=${MACHINE_TYPE:-e2-standard-2}
    local num_nodes=${NUM_NODES:-2}
    
    print_status "Cluster configuration:"
    print_status "  Name: ${cluster_name}"
    print_status "  Zone: ${zone}"
    print_status "  Machine type: ${machine_type}"
    print_status "  Number of nodes: ${num_nodes}"
    echo ""
    
    print_status "Creating cluster (this may take several minutes)..."
    
    gcloud container clusters create ${cluster_name} \
        --zone=${zone} \
        --machine-type=${machine_type} \
        --num-nodes=${num_nodes} \
        --enable-autoscaling \
        --min-nodes=1 \
        --max-nodes=5 \
        --enable-autorepair \
        --enable-autoupgrade \
        --project=${PROJECT_ID}
    
    if [ $? -eq 0 ]; then
        print_status "Cluster created successfully!"
        print_status "Getting cluster credentials..."
        gcloud container clusters get-credentials ${cluster_name} --zone=${zone} --project=${PROJECT_ID}
    else
        print_error "Failed to create cluster"
        exit 1
    fi
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
    print_status "Cluster: ${CLUSTER_NAME}, Zone: ${ZONE}, Project: ${PROJECT_ID}"
    
    if ! gcloud container clusters get-credentials ${CLUSTER_NAME} \
        --zone ${ZONE} \
        --project ${PROJECT_ID} 2>/dev/null; then
        
        print_error "Failed to get credentials for cluster '${CLUSTER_NAME}' in zone '${ZONE}'"
        print_status "Available clusters:"
        gcloud container clusters list --format="table(name,location,status)" --filter="status:RUNNING"
        echo ""
        print_status "To list all available clusters, run: $0 list"
        print_status "To create a new cluster, run: $0 create"
        print_status "To use a different cluster, set CLUSTER_NAME and ZONE environment variables"
        exit 1
    fi
    
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
    
    # Build images with GCR registry
    scripts/build-containers.sh --registry ${REGISTRY}
    
    # Tag and push images to GCR
    local images=("ragme-frontend" "ragme-api" "ragme-mcp" "ragme-agent")
    
    for image in "${images[@]}"; do
        print_status "Tagging and pushing ${image}..."
        
        # For GKE, images are already built with GCR registry format
        # Just push the existing GCR image
        podman push ${REGISTRY}/${image}:${IMAGE_TAG}
        
        print_status "${image} pushed successfully"
    done
    
    print_status "All images built and pushed to GCR"
}

# Function to create ConfigMap and Secrets
create_config() {
    print_status "Creating ConfigMap and Secrets..."
    
    # Get external LoadBalancer IP for OAuth redirect URIs
    local external_ip=""
    if kubectl get service -n ${NAMESPACE} ragme-frontend-lb >/dev/null 2>&1; then
        external_ip=$(kubectl get service -n ${NAMESPACE} ragme-frontend-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    fi
    
    # Fallback to localhost if no external IP found
    if [ -z "$external_ip" ]; then
        external_ip="localhost"
        print_warning "No external LoadBalancer IP found, using localhost for OAuth redirect URIs"
    else
        print_status "Using external IP $external_ip for OAuth redirect URIs"
    fi
    
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
    
    # Read vector database configuration from .env file
    local vector_db_type="weaviate-local"
    local vector_db_text_collection="ragme-text-collection"
    local vector_db_image_collection="ragme-image-collection"
    local weaviate_url="your-weaviate-url-here"
    local weaviate_api_key="your-weaviate-api-key-here"
    local openai_api_key="your-openai-api-key-here"
    
    # OAuth configuration defaults
    local google_oauth_client_id="your-google-oauth-client-id"
    local google_oauth_client_secret="your-google-oauth-client-secret"
    local github_oauth_client_id="your-github-oauth-client-id"
    local github_oauth_client_secret="your-github-oauth-client-secret"
    local apple_oauth_client_id="your-apple-oauth-client-id"
    local apple_oauth_client_secret="your-apple-oauth-client-secret"
    
    if grep -q "^VECTOR_DB_TYPE=" ../.env; then
        vector_db_type=$(grep "^VECTOR_DB_TYPE=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^VECTOR_DB_TEXT_COLLECTION_NAME=" ../.env; then
        vector_db_text_collection=$(grep "^VECTOR_DB_TEXT_COLLECTION_NAME=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^VECTOR_DB_IMAGE_COLLECTION_NAME=" ../.env; then
        vector_db_image_collection=$(grep "^VECTOR_DB_IMAGE_COLLECTION_NAME=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^WEAVIATE_URL=" ../.env; then
        weaviate_url=$(grep "^WEAVIATE_URL=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^WEAVIATE_API_KEY=" ../.env; then
        weaviate_api_key=$(grep "^WEAVIATE_API_KEY=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^OPENAI_API_KEY=" ../.env; then
        openai_api_key=$(grep "^OPENAI_API_KEY=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    # Read OAuth configuration from .env file
    if grep -q "^GOOGLE_OAUTH_CLIENT_ID=" ../.env; then
        google_oauth_client_id=$(grep "^GOOGLE_OAUTH_CLIENT_ID=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^GOOGLE_OAUTH_CLIENT_SECRET=" ../.env; then
        google_oauth_client_secret=$(grep "^GOOGLE_OAUTH_CLIENT_SECRET=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^GITHUB_OAUTH_CLIENT_ID=" ../.env; then
        github_oauth_client_id=$(grep "^GITHUB_OAUTH_CLIENT_ID=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^GITHUB_OAUTH_CLIENT_SECRET=" ../.env; then
        github_oauth_client_secret=$(grep "^GITHUB_OAUTH_CLIENT_SECRET=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^APPLE_OAUTH_CLIENT_ID=" ../.env; then
        apple_oauth_client_id=$(grep "^APPLE_OAUTH_CLIENT_ID=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    if grep -q "^APPLE_OAUTH_CLIENT_SECRET=" ../.env; then
        apple_oauth_client_secret=$(grep "^APPLE_OAUTH_CLIENT_SECRET=" ../.env | cut -d'=' -f2 | tr -d '"')
    fi
    
    print_status "Using vector database configuration from .env:"
    print_status "  VECTOR_DB_TYPE: $vector_db_type"
    print_status "  VECTOR_DB_TEXT_COLLECTION_NAME: $vector_db_text_collection"
    print_status "  VECTOR_DB_IMAGE_COLLECTION_NAME: $vector_db_image_collection"
    print_status "  WEAVIATE_URL: $weaviate_url"
    print_status "  WEAVIATE_API_KEY: [REDACTED]"
    print_status "  OPENAI_API_KEY: [REDACTED]"
    print_status "Using OAuth configuration from .env:"
    print_status "  GOOGLE_OAUTH_CLIENT_ID: $google_oauth_client_id"
    print_status "  GOOGLE_OAUTH_CLIENT_SECRET: [REDACTED]"
    print_status "  GITHUB_OAUTH_CLIENT_ID: $github_oauth_client_id"
    print_status "  GITHUB_OAUTH_CLIENT_SECRET: [REDACTED]"
    print_status "  APPLE_OAUTH_CLIENT_ID: $apple_oauth_client_id"
    print_status "  APPLE_OAUTH_CLIENT_SECRET: [REDACTED]"
    
    # Update the static configmap-gke.yaml file with values from .env
    print_status "Updating static configmap-gke.yaml with .env values..."
    local configmap_file="gke/k8s/configmap-gke.yaml"
    
    # Update VECTOR_DB_TYPE
    sed -i.bak "s/VECTOR_DB_TYPE: \".*\"/VECTOR_DB_TYPE: \"$vector_db_type\"/" "$configmap_file"
    
    # Update VECTOR_DB_TEXT_COLLECTION_NAME
    sed -i.bak "s/VECTOR_DB_TEXT_COLLECTION_NAME: \".*\"/VECTOR_DB_TEXT_COLLECTION_NAME: \"$vector_db_text_collection\"/" "$configmap_file"
    
    # Update VECTOR_DB_IMAGE_COLLECTION_NAME
    sed -i.bak "s/VECTOR_DB_IMAGE_COLLECTION_NAME: \".*\"/VECTOR_DB_IMAGE_COLLECTION_NAME: \"$vector_db_image_collection\"/" "$configmap_file"
    
    # Update WEAVIATE_URL
    sed -i.bak "s/WEAVIATE_URL: \".*\"/WEAVIATE_URL: \"$weaviate_url\"/" "$configmap_file"
    
    # Update WEAVIATE_API_KEY
    sed -i.bak "s/WEAVIATE_API_KEY: \".*\"/WEAVIATE_API_KEY: \"$weaviate_api_key\"/" "$configmap_file"
    
    # Update OPENAI_API_KEY
    sed -i.bak "s/OPENAI_API_KEY: \".*\"/OPENAI_API_KEY: \"$openai_api_key\"/" "$configmap_file"
    
    # Update OAuth configuration
    sed -i.bak "s/GOOGLE_OAUTH_CLIENT_ID: \".*\"/GOOGLE_OAUTH_CLIENT_ID: \"$google_oauth_client_id\"/" "$configmap_file"
    sed -i.bak "s/GOOGLE_OAUTH_CLIENT_SECRET: \".*\"/GOOGLE_OAUTH_CLIENT_SECRET: \"$google_oauth_client_secret\"/" "$configmap_file"
    sed -i.bak "s/GITHUB_OAUTH_CLIENT_ID: \".*\"/GITHUB_OAUTH_CLIENT_ID: \"$github_oauth_client_id\"/" "$configmap_file"
    sed -i.bak "s/GITHUB_OAUTH_CLIENT_SECRET: \".*\"/GITHUB_OAUTH_CLIENT_SECRET: \"$github_oauth_client_secret\"/" "$configmap_file"
    sed -i.bak "s/APPLE_OAUTH_CLIENT_ID: \".*\"/APPLE_OAUTH_CLIENT_ID: \"$apple_oauth_client_id\"/" "$configmap_file"
    sed -i.bak "s/APPLE_OAUTH_CLIENT_SECRET: \".*\"/APPLE_OAUTH_CLIENT_SECRET: \"$apple_oauth_client_secret\"/" "$configmap_file"
    
    # Clean up backup files
    rm -f "$configmap_file.bak"
    
    print_status "Updated $configmap_file with .env values"
    
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
  VECTOR_DB_TYPE: "${vector_db_type}"
  VECTOR_DB_TEXT_COLLECTION_NAME: "${vector_db_text_collection}"
  VECTOR_DB_IMAGE_COLLECTION_NAME: "${vector_db_image_collection}"
  
  # MinIO Configuration
  MINIO_ENDPOINT: "ragme-minio:9000"
  
  # OAuth Redirect URIs (external LoadBalancer IP)
  GOOGLE_OAUTH_REDIRECT_URI: "http://${external_ip}/auth/google/callback"
  GITHUB_OAUTH_REDIRECT_URI: "http://${external_ip}/auth/github/callback"
  APPLE_OAUTH_REDIRECT_URI: "http://${external_ip}/auth/apple/callback"
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
            sed "s|:latest|:${IMAGE_TAG}|g" "$temp_manifest" > "${temp_manifest}.tmp" && mv "${temp_manifest}.tmp" "$temp_manifest"
            
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

# Cleanup secrets from configmap file
cleanup_secrets() {
    print_header "Cleaning up secrets from configmap-gke.yaml"
    
    local configmap_file="gke/k8s/configmap-gke.yaml"
    
    if [[ ! -f "$configmap_file" ]]; then
        print_error "ConfigMap file not found: $configmap_file"
        exit 1
    fi
    
    print_status "Restoring placeholder values in $configmap_file..."
    
    # Restore placeholder values for all secrets
    sed -i.bak "s/WEAVIATE_API_KEY: \".*\"/WEAVIATE_API_KEY: \"your-weaviate-api-key-here\"/" "$configmap_file"
    sed -i.bak "s/WEAVIATE_URL: \".*\"/WEAVIATE_URL: \"your-weaviate-url-here\"/" "$configmap_file"
    sed -i.bak "s/OPENAI_API_KEY: \".*\"/OPENAI_API_KEY: \"your-openai-api-key-here\"/" "$configmap_file"
    sed -i.bak "s/GOOGLE_OAUTH_CLIENT_ID: \".*\"/GOOGLE_OAUTH_CLIENT_ID: \"your-google-oauth-client-id\"/" "$configmap_file"
    sed -i.bak "s/GOOGLE_OAUTH_CLIENT_SECRET: \".*\"/GOOGLE_OAUTH_CLIENT_SECRET: \"your-google-oauth-client-secret\"/" "$configmap_file"
    sed -i.bak "s/GITHUB_OAUTH_CLIENT_ID: \".*\"/GITHUB_OAUTH_CLIENT_ID: \"your-github-oauth-client-id\"/" "$configmap_file"
    sed -i.bak "s/GITHUB_OAUTH_CLIENT_SECRET: \".*\"/GITHUB_OAUTH_CLIENT_SECRET: \"your-github-oauth-client-secret\"/" "$configmap_file"
    sed -i.bak "s/APPLE_OAUTH_CLIENT_ID: \".*\"/APPLE_OAUTH_CLIENT_ID: \"your-apple-oauth-client-id\"/" "$configmap_file"
    sed -i.bak "s/APPLE_OAUTH_CLIENT_SECRET: \".*\"/APPLE_OAUTH_CLIENT_SECRET: \"your-apple-oauth-client-secret\"/" "$configmap_file"
    
    # Remove backup file
    rm -f "$configmap_file.bak"
    
    print_status "Secrets cleaned up from $configmap_file"
    print_status "File is now safe to commit to repository"
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
        "list")
            check_dependencies
            list_clusters
            ;;
        "create")
            check_dependencies
            create_cluster
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
        "cleanup-secrets")
            cleanup_secrets
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
