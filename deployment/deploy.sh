#!/bin/bash

# RAGme Kubernetes Deployment Script
# Deploys RAGme services to a local kind cluster

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
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

# Configuration
CLUSTER_NAME=${CLUSTER_NAME:-ragme-cluster}
REGISTRY=${REGISTRY:-localhost:5001}
IMAGE_TAG=${IMAGE_TAG:-latest}

# Navigate to project root
cd "$(dirname "$0")"

# Function to show help
show_help() {
    echo -e "${BLUE}RAGme Kubernetes Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  help      - Show this help message"
    echo "  setup     - Install required dependencies (kind, kubectl, podman, golang)"
    echo "  deploy    - Full deployment (default): create cluster, build images, deploy services"
    echo "  build     - Build and load container images only"
    echo "  status    - Show deployment status and access URLs"
    echo "  destroy   - Delete the entire deployment and cluster"
    echo "  cluster   - Create kind cluster and registry only"
    echo "  minikube  - Create minikube cluster and registry only"
    echo ""
    echo "Environment variables:"
    echo "  CLUSTER_NAME  - Kind cluster name (default: ragme-cluster)"
    echo "  CLUSTER_TYPE  - Cluster type: kind or minikube (default: kind)"
    echo "  REGISTRY      - Container registry (default: localhost:5001)"
    echo "  IMAGE_TAG     - Image tag (default: latest)"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Install dependencies"
    echo "  $0                          # Full deployment"
    echo "  $0 deploy                   # Full deployment"
    echo "  $0 status                   # Show status"
    echo "  $0 destroy                  # Clean up everything"
    echo ""
    echo "Note: On macOS, Podman requires a Linux VM to run containers."
    echo "The script will automatically create and start a 'ragme-machine' if needed."
    echo ""
    echo "Note: Ingress ports 80/443 are mapped to 8080/8443 to avoid privileged port issues."
    echo ""
    echo "For more information, visit: https://github.com/maximilien/ragme-io"
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to detect architecture
detect_arch() {
    case "$(uname -m)" in
        x86_64) echo "amd64" ;;
        aarch64) echo "arm64" ;;
        arm64) echo "arm64" ;;
        *) echo "unknown" ;;
    esac
}

# Function to install kind
install_kind() {
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]] || [[ "$arch" == "unknown" ]]; then
        print_error "Unsupported OS or architecture. Please install kind manually."
        return 1
    fi
    
    print_status "Installing kind..."
    
    if [[ "$os" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install kind
        else
            print_error "Homebrew not found. Please install Homebrew first or install kind manually."
            return 1
        fi
    else
        local kind_version="v0.20.0"
        local kind_url="https://kind.sigs.k8s.io/dl/${kind_version}/kind-${os}-${arch}"
        
        curl -Lo ./kind "$kind_url"
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
    fi
    
    print_status "kind installed successfully"
}

# Function to install kubectl
install_kubectl() {
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]] || [[ "$arch" == "unknown" ]]; then
        print_error "Unsupported OS or architecture. Please install kubectl manually."
        return 1
    fi
    
    print_status "Installing kubectl..."
    
    if [[ "$os" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install kubectl
        else
            print_error "Homebrew not found. Please install Homebrew first or install kubectl manually."
            return 1
        fi
    else
        local kubectl_version="v1.28.0"
        local kubectl_url="https://dl.k8s.io/release/${kubectl_version}/bin/${os}/${arch}/kubectl"
        
        curl -LO "$kubectl_url"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    fi
    
    print_status "kubectl installed successfully"
}

# Function to install podman
install_podman() {
    local os=$(detect_os)
    
    print_status "Installing podman..."
    
    if [[ "$os" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install podman
            print_status "Podman installed. On macOS, you'll need to initialize a machine:"
            echo "  podman machine init"
            echo "  podman machine start"
        else
            print_error "Homebrew not found. Please install Homebrew first or install podman manually."
            return 1
        fi
    elif [[ "$os" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y podman
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y podman
        elif command -v yum &> /dev/null; then
            sudo yum install -y podman
        else
            print_error "Unsupported package manager. Please install podman manually."
            return 1
        fi
    else
        print_error "Unsupported OS. Please install podman manually."
        return 1
    fi
    
    print_status "podman installed successfully"
}

# Function to install golang
install_golang() {
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]] || [[ "$arch" == "unknown" ]]; then
        print_error "Unsupported OS or architecture. Please install golang manually."
        return 1
    fi
    
    print_status "Installing golang..."
    
    if [[ "$os" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install go
        else
            print_error "Homebrew not found. Please install Homebrew first or install golang manually."
            return 1
        fi
    else
        local go_version="1.21.0"
        local go_url="https://go.dev/dl/go${go_version}.${os}-${arch}.tar.gz"
        
        curl -LO "$go_url"
        sudo rm -rf /usr/local/go
        sudo tar -C /usr/local -xzf "go${go_version}.${os}-${arch}.tar.gz"
        rm "go${go_version}.${os}-${arch}.tar.gz"
        
        # Add to PATH if not already there
        if ! grep -q "/usr/local/go/bin" ~/.bashrc 2>/dev/null; then
            echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
            export PATH=$PATH:/usr/local/go/bin
        fi
    fi
    
    print_status "golang installed successfully"
}

# Function to setup dependencies
setup_dependencies() {
    print_header "Setting up RAGme deployment dependencies"
    
    local missing_deps=()
    
    # Check kind
    if ! command -v kind &> /dev/null; then
        missing_deps+=("kind")
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    fi
    
    # Check podman
    if ! command -v podman &> /dev/null; then
        missing_deps+=("podman")
    fi
    
    # Check golang
    if ! command -v go &> /dev/null; then
        missing_deps+=("golang")
    fi
    
    if [[ ${#missing_deps[@]} -eq 0 ]]; then
        print_status "All dependencies are already installed!"
        return 0
    fi
    
    print_status "Missing dependencies: ${missing_deps[*]}"
    echo ""
    
    for dep in "${missing_deps[@]}"; do
        case "$dep" in
            "kind")
                install_kind
                ;;
            "kubectl")
                install_kubectl
                ;;
            "podman")
                install_podman
                ;;
            "golang")
                install_golang
                ;;
        esac
    done
    
    print_status "Dependency setup completed!"
    echo ""
    print_status "Please restart your terminal or run 'source ~/.bashrc' to ensure PATH is updated."
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v kind &> /dev/null; then
        missing_deps+=("kind")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    fi
    
    if ! command -v podman &> /dev/null; then
        missing_deps+=("podman")
    fi
    
    if ! command -v go &> /dev/null; then
        missing_deps+=("golang")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        print_status "Run '$0 setup' to install missing dependencies automatically."
        echo "Or install them manually:"
        echo "  - kind: https://kind.sigs.k8s.io/docs/user/quick-start/"
        echo "  - kubectl: https://kubernetes.io/docs/tasks/tools/"
        echo "  - podman: https://podman.io/getting-started/installation"
        echo "  - golang: https://golang.org/doc/install"
        exit 1
    fi
    
    print_status "All dependencies are available"
    
    # Check Podman machine on macOS
    if [[ "$(detect_os)" == "macos" ]]; then
        check_podman_machine
    fi
}

# Function to check and initialize Podman machine on macOS
check_podman_machine() {
    print_status "Checking Podman machine status on macOS..."
    
    if ! podman machine list | grep -q "Currently running"; then
        print_warning "Podman machine is not running. Attempting to start it..."
        
        if ! podman machine list | grep -q "ragme-machine"; then
            print_status "Creating Podman machine 'ragme-machine'..."
            podman machine init ragme-machine
        fi
        
        print_status "Starting Podman machine..."
        podman machine start ragme-machine
        
        # Wait longer for the machine to be ready and retry
        print_status "Waiting for Podman machine to be ready..."
        local attempts=0
        local max_attempts=10
        
        while [[ $attempts -lt $max_attempts ]]; do
            sleep 2
            if podman machine list | grep -q "Currently running"; then
                print_status "Podman machine is running"
                return 0
            fi
            attempts=$((attempts + 1))
            print_status "Waiting for machine to start... (attempt $attempts/$max_attempts)"
        done
        
        print_error "Failed to start Podman machine after $max_attempts attempts. Please run manually:"
        echo "  podman machine init ragme-machine"
        echo "  podman machine start ragme-machine"
        exit 1
    fi
    
    print_status "Podman machine is running"
}

# Function to push images to local registry
push_to_registry() {
    print_status "Attempting to push images to local registry..."
    
    # Tag images for local registry
    podman tag ragme-api:latest $REGISTRY/ragme-api:$IMAGE_TAG
    podman tag ragme-mcp:latest $REGISTRY/ragme-mcp:$IMAGE_TAG
    podman tag ragme-agent:latest $REGISTRY/ragme-agent:$IMAGE_TAG
    podman tag ragme-frontend:latest $REGISTRY/ragme-frontend:$IMAGE_TAG
    
    # Try to push to local registry
    if podman push $REGISTRY/ragme-api:$IMAGE_TAG 2>/dev/null && \
       podman push $REGISTRY/ragme-mcp:$IMAGE_TAG 2>/dev/null && \
       podman push $REGISTRY/ragme-agent:$IMAGE_TAG 2>/dev/null && \
       podman push $REGISTRY/ragme-frontend:$IMAGE_TAG 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to load images directly into kind
load_images_directly() {
    print_status "Loading images directly into kind cluster..."
    
    # Since we're using Podman, we need to use the podman-specific approach
    # Create a tar file and load it into kind
    print_status "Creating image tar files for kind..."
    
    # Create tar files from Podman images
    podman save ragme-api:latest -o ragme-api.tar
    podman save ragme-mcp:latest -o ragme-mcp.tar
    podman save ragme-agent:latest -o ragme-agent.tar
    podman save ragme-frontend:latest -o ragme-frontend.tar
    
    # Load tar files into kind
    kind load image-archive ragme-api.tar --name $CLUSTER_NAME
    kind load image-archive ragme-mcp.tar --name $CLUSTER_NAME
    kind load image-archive ragme-agent.tar --name $CLUSTER_NAME
    kind load image-archive ragme-frontend.tar --name $CLUSTER_NAME
    
    # Clean up tar files
    rm -f ragme-api.tar ragme-mcp.tar ragme-agent.tar ragme-frontend.tar
    
    print_status "Images loaded directly into kind cluster"
}

# Function to create minikube cluster
create_minikube_cluster() {
    print_status "Creating Minikube cluster with 8GB memory..."
    
    # Check if minikube is available
    if ! command -v minikube &> /dev/null; then
        print_error "Minikube is not installed. Please install it first:"
        print_status "  brew install minikube"
        exit 1
    fi
    
    # Stop any existing minikube cluster
    minikube stop 2>/dev/null || true
    minikube delete 2>/dev/null || true
    
    # Start minikube with 7GB memory (leaving some for system)
    print_status "Starting Minikube with 7GB memory..."
    minikube start --memory=7168 --cpus=4 --driver=podman
    
    # Enable addons
    print_status "Enabling Minikube addons..."
    minikube addons enable ingress
    minikube addons enable storage-provisioner
    
    # Set kubectl context
    minikube kubectl -- cluster-info
    
    print_status "Minikube cluster created successfully with 8GB memory"
}

# Function to create kind cluster
create_cluster() {
    print_status "Creating kind cluster: $CLUSTER_NAME"
    
    # Create kind cluster config
    cat > kind-config.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $CLUSTER_NAME
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
  - containerPort: 443
    hostPort: 8443
    protocol: TCP
  - containerPort: 30020  # Frontend
    hostPort: 30020
    protocol: TCP
  - containerPort: 30021  # API
    hostPort: 30021
    protocol: TCP
  - containerPort: 30022  # MCP
    hostPort: 30022
    protocol: TCP
  - containerPort: 30900  # MinIO API
    hostPort: 30900
    protocol: TCP
  - containerPort: 30901  # MinIO Console
    hostPort: 30901
    protocol: TCP
  - containerPort: 30080  # Weaviate
    hostPort: 30080
    protocol: TCP
- role: worker
  kubeadmConfigPatches:
  - |
    kind: JoinConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        system-reserved: memory=256Mi
        kube-reserved: memory=256Mi
EOF

    # Create cluster with increased memory for worker node
    # Use Docker for better memory management support
    export KIND_NODE_IMAGE=kindest/node:v1.34.0
    
    # Choose between Kind and Minikube
    if [[ "${CLUSTER_TYPE:-kind}" == "minikube" ]]; then
        print_status "Using Minikube for cluster creation"
        create_minikube_cluster
    else
        print_status "Using Kind with Podman for cluster creation"
        export KIND_EXPERIMENTAL_PROVIDER=podman
        
        # Create a custom kind configuration with memory limits
        cat > kind-config-8gb.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $CLUSTER_NAME
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
        system-reserved: memory=1Gi
        kube-reserved: memory=1Gi
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
  - containerPort: 443
    hostPort: 8443
    protocol: TCP
  - containerPort: 30020  # Frontend
    hostPort: 30020
    protocol: TCP
  - containerPort: 30021  # API
    hostPort: 30021
    protocol: TCP
  - containerPort: 30022  # MCP
    hostPort: 30022
    protocol: TCP
  - containerPort: 30900  # MinIO API
    hostPort: 30900
    protocol: TCP
  - containerPort: 30901  # MinIO Console
    hostPort: 30901
    protocol: TCP
  - containerPort: 30080  # Weaviate
    hostPort: 30080
    protocol: TCP
- role: worker
  kubeadmConfigPatches:
  - |
    kind: JoinConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        system-reserved: memory=1Gi
        kube-reserved: memory=1Gi
EOF
    fi
    
    if [[ "${CLUSTER_TYPE:-kind}" == "minikube" ]]; then
        # Minikube cluster already created
        print_status "Minikube cluster ready"
    else
        # Create the kind cluster with 8GB configuration
        kind create cluster --config kind-config-8gb.yaml --name $CLUSTER_NAME
        
        # After cluster creation, manually set container memory to 8GB
        print_status "Setting worker node memory to 8GB..."
        sleep 10  # Wait for containers to be fully created
        
        local worker_container=$(podman ps --filter "name=ragme-cluster-worker" --format "{{.ID}}")
        if [[ -n "$worker_container" ]]; then
            print_status "Found worker container: $worker_container"
            print_status "Setting memory limits to 8GB..."
            podman update --memory=8g --memory-swap=8g "$worker_container"
            print_status "Worker node memory set to 8GB"
        else
            print_warning "Could not find worker node container"
        fi
    fi
    
    print_status "Cluster created with 8GB memory configuration."
    
    # Set kubectl context
    kubectl cluster-info --context kind-$CLUSTER_NAME
}

# Function to setup local registry
setup_registry() {
    print_status "Setting up local registry..."
    
    if [[ "$KIND_EXPERIMENTAL_PROVIDER" == "docker" ]]; then
        # Docker registry setup
        if docker ps | grep -q kind-registry; then
            print_status "Docker registry already running"
            return 0
        fi
        
        if docker ps -a | grep -q kind-registry; then
            print_status "Docker registry container exists but not running, starting it..."
            docker start kind-registry
            return 0
        fi
        
        print_status "Starting Docker local registry..."
        docker run -d --name kind-registry --network=kind -p 5001:5000 registry:2
        
        # Connect registry to kind network
        if ! docker network exists kind; then
            docker network create kind
        fi
        
        docker network connect kind kind-registry 2>/dev/null || true
    else
        # Podman registry setup
        if podman ps | grep -q kind-registry; then
            print_status "Podman registry already running"
            return 0
        fi
        
        if podman ps -a | grep -q kind-registry; then
            print_status "Podman registry container exists but not running, starting it..."
            podman start kind-registry
            return 0
        fi
        
        print_status "Starting Podman local registry..."
        podman run -d --name kind-registry --network=kind -p 5001:5000 registry:2
        
        # Connect registry to kind network
        if ! podman network exists kind; then
            podman network create kind
        fi
        
        podman network connect kind kind-registry 2>/dev/null || true
    fi
}

# Function to build and load images
build_and_load_images() {
    print_status "Building RAGme container images..."
    
    # The build script is in the deployment/scripts directory
    local script_dir="$(pwd)/scripts"
    
    print_status "Building containers from: $script_dir"
    
    if [[ -f "$script_dir/build-containers.sh" ]]; then
        cd "$script_dir"
        ./build-containers.sh
        cd ..
    else
        print_error "Build script not found at: $script_dir/build-containers.sh"
        print_status "Please ensure you're running from the deployment directory"
        exit 1
    fi
    
    print_status "Loading images into kind cluster..."
    
    # Try to push to local registry first, fallback to direct loading if that fails
    if push_to_registry; then
        print_status "Successfully pushed images to local registry"
    else
        print_warning "Failed to push to local registry, loading images directly into kind"
        load_images_directly
    fi
}

# Function to generate configmap from .env file
generate_configmap() {
    print_status "Generating Kubernetes configmap from .env file..."
    
    # Check if .env file exists
    if [ ! -f "../.env" ]; then
        print_error ".env file not found in project root"
        return 1
    fi
    
    # Source the .env file
    set -a
    source ../.env
    set +a
    
    # Create a temporary configmap file
    cat > k8s/configmap-generated.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ragme-config
  namespace: ragme
  labels:
    app: ragme
data:
  # RAGme Configuration
  RAGME_API_PORT: "8021"
  RAGME_MCP_PORT: "8022"
  RAGME_FRONTEND_PORT: "8020"
  
  # Service URLs (external access for frontend)
  RAGME_API_URL: "http://localhost:30021"
  RAGME_MCP_URL: "http://localhost:30022"
  
  # Vector Database Configuration
  VECTOR_DB_TYPE: "${VECTOR_DB_TYPE:-weaviate}"
  VECTOR_DB_TEXT_COLLECTION_NAME: "${VECTOR_DB_TEXT_COLLECTION_NAME:-ragme-text-docs}"
  VECTOR_DB_IMAGE_COLLECTION_NAME: "${VECTOR_DB_IMAGE_COLLECTION_NAME:-ragme-image-docs}"
  
  # MinIO Configuration
  MINIO_ENDPOINT: "ragme-minio:9000"
  
  # Application Configuration
  APPLICATION_NAME: "${APPLICATION_NAME:-RAGme Kubernetes}"
  APPLICATION_VERSION: "${APPLICATION_VERSION:-1.0.0}"
  APPLICATION_TITLE: "${APPLICATION_TITLE:-RAGme AI Assistant}"
  APPLICATION_DESCRIPTION: "${APPLICATION_DESCRIPTION:-AI-powered document and image processing assistant}"
  
  # Watch Directory
  WATCH_DIRECTORY: "${WATCH_DIRECTORY:-/app/watch_directory}"
  MINIO_LOCAL_PATH: "${MINIO_LOCAL_PATH:-/app/minio_data}"
  
  # OAuth Configuration
  GOOGLE_OAUTH_REDIRECT_URI: "http://ragme-api:8021/auth/google/callback"
  GITHUB_OAUTH_REDIRECT_URI: "http://ragme-api:8021/auth/github/callback"
  APPLE_OAUTH_REDIRECT_URI: "http://ragme-api:8021/auth/apple/callback"
---
apiVersion: v1
kind: Secret
metadata:
  name: ragme-secrets
  namespace: ragme
  labels:
    app: ragme
type: Opaque
stringData:
  # Required secrets - update these values
  OPENAI_API_KEY: "${OPENAI_API_KEY}"
  
  # Optional secrets for external services
  WEAVIATE_API_KEY: "${WEAVIATE_API_KEY}"
  WEAVIATE_URL: "${WEAVIATE_URL}"
  MILVUS_URI: "${MILVUS_URI:-your-milvus-uri}"
  MILVUS_TOKEN: "${MILVUS_TOKEN:-your-milvus-token}"
  
  # MinIO credentials
  MINIO_ACCESS_KEY: "minioadmin"
  MINIO_SECRET_KEY: "minioadmin"
  
  # S3 credentials (if using S3 instead of MinIO)
  S3_ENDPOINT: "${S3_ENDPOINT:-your-s3-endpoint}"
  S3_ACCESS_KEY: "${S3_ACCESS_KEY:-your-s3-access-key}"
  S3_SECRET_KEY: "${S3_SECRET_KEY:-your-s3-secret-key}"
  S3_BUCKET_NAME: "${S3_BUCKET_NAME:-your-s3-bucket}"
  S3_REGION: "${S3_REGION:-us-east-1}"
  
  # OAuth secrets - update these values
  GOOGLE_OAUTH_CLIENT_ID: "${GOOGLE_OAUTH_CLIENT_ID:-your-google-oauth-client-id}"
  GOOGLE_OAUTH_CLIENT_SECRET: "${GOOGLE_OAUTH_CLIENT_SECRET:-your-google-oauth-client-secret}"
  GITHUB_OAUTH_CLIENT_ID: "${GITHUB_OAUTH_CLIENT_ID:-your-github-oauth-client-id}"
  GITHUB_OAUTH_CLIENT_SECRET: "${GITHUB_OAUTH_CLIENT_SECRET:-your-github-oauth-client-secret}"
  APPLE_OAUTH_CLIENT_ID: "${APPLE_OAUTH_CLIENT_ID:-your-apple-oauth-client-id}"
  APPLE_OAUTH_CLIENT_SECRET: "${APPLE_OAUTH_CLIENT_SECRET:-your-apple-oauth-client-secret}"
  
  # Session configuration
  SESSION_SECRET_KEY: "${SESSION_SECRET_KEY:-ragme-shared-session-secret-key-2025}"
EOF
    
    print_status "Configmap generated from .env file"
}

# Function to deploy services
deploy_services() {
    print_status "Deploying RAGme services to Kubernetes..."
    
    # Generate configmap from .env file
    generate_configmap
    
    # Apply the generated configmap first
    kubectl apply -f k8s/configmap-generated.yaml
    
    # Apply kustomization
    kubectl apply -k k8s/
    
    print_status "Waiting for deployments to be ready..."
    
    # Wait for deployments
    kubectl wait --for=condition=available --timeout=300s deployment/ragme-minio -n ragme
    kubectl wait --for=condition=available --timeout=300s deployment/ragme-api -n ragme
    kubectl wait --for=condition=available --timeout=300s deployment/ragme-mcp -n ragme
    kubectl wait --for=condition=available --timeout=300s deployment/ragme-agent -n ragme
    kubectl wait --for=condition=available --timeout=300s deployment/ragme-frontend -n ragme
}

# Function to show deployment status
show_status() {
    print_header "Deployment Status"
    
    echo ""
    print_status "Pods:"
    kubectl get pods -n ragme
    
    echo ""
    print_status "Services:"
    kubectl get services -n ragme
    
    echo ""
    print_status "Access URLs:"
    echo "  Frontend:     http://localhost:30020"
    echo "  API:          http://localhost:30021"
    echo "  MCP:          http://localhost:30022"
    echo "  MinIO API:    http://localhost:30900"
    echo "  MinIO Console: http://localhost:30901"
    echo "  Weaviate:     http://localhost:30080"
    echo "  Ingress HTTP: http://localhost:8080"
    echo "  Ingress HTTPS: https://localhost:8443"
    
    echo ""
    print_status "To check logs:"
    echo "  kubectl logs -f deployment/ragme-api -n ragme"
    echo "  kubectl logs -f deployment/ragme-mcp -n ragme"
    echo "  kubectl logs -f deployment/ragme-agent -n ragme"
    echo "  kubectl logs -f deployment/ragme-frontend -n ragme"
    
    echo ""
    print_status "To delete the deployment:"
    echo "  kubectl delete namespace ragme"
    echo "  kind delete cluster --name $CLUSTER_NAME"
}

# Main deployment process
case "${1:-deploy}" in
    "help")
        show_help
        ;;
    "setup")
        setup_dependencies
        ;;
    "deploy")
        print_header "Starting RAGme deployment to kind cluster"
        
        # Check dependencies before proceeding
        check_dependencies
        
        # Check if cluster exists (handle both Docker and Podman)
        if [[ "$KIND_EXPERIMENTAL_PROVIDER" == "podman" ]]; then
            # For Podman, check if containers exist
            if podman ps --filter "name=ragme-cluster" --format "{{.Names}}" | grep -q "ragme-cluster"; then
                print_status "Kind cluster '$CLUSTER_NAME' already exists (Podman)"
            else
                create_cluster
            fi
        else
            # For Docker, use kind get clusters
            if ! kind get clusters | grep -q "^$CLUSTER_NAME$"; then
                create_cluster
            else
                print_status "Kind cluster '$CLUSTER_NAME' already exists (Docker)"
            fi
        fi
        
        setup_registry
        build_and_load_images
        deploy_services
        show_status
        
        # Clean up generated configmap file
        rm -f k8s/configmap-generated.yaml
        ;;
        
    "build")
        print_header "Building container images only"
        check_dependencies
        build_and_load_images
        ;;
        
    "status")
        print_header "Showing deployment status"
        check_dependencies
        show_status
        ;;
        
    "destroy")
        print_header "Destroying RAGme deployment"
        check_dependencies
        kubectl delete namespace ragme --ignore-not-found
        
        if [[ "${CLUSTER_TYPE:-kind}" == "minikube" ]]; then
            minikube stop 2>/dev/null || true
            minikube delete 2>/dev/null || true
            print_status "Minikube cluster destroyed"
        else
            kind delete cluster --name $CLUSTER_NAME
            print_status "Kind cluster destroyed"
        fi
        
        podman rm -f kind-registry 2>/dev/null || true
        
        # Clean up generated files
        rm -f k8s/configmap-generated.yaml
        
        print_status "Deployment destroyed successfully"
        ;;
        
    "cluster")
        print_header "Creating kind cluster and registry"
        check_dependencies
        create_cluster
        setup_registry
        ;;
        
    "minikube")
        print_header "Creating minikube cluster and registry"
        check_dependencies
        create_cluster
        setup_registry
        ;;
        
    *)
        show_help
        ;;
esac