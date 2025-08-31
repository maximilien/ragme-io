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

print_header "RAGme Kubernetes Deployment"

# Check dependencies
print_status "Checking dependencies..."

if ! command -v kind &> /dev/null; then
    print_error "kind is not installed. Please install kind first:"
    echo "  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64"
    echo "  chmod +x ./kind"
    echo "  sudo mv ./kind /usr/local/bin/kind"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first:"
    echo "  curl -LO https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl"
    echo "  chmod +x kubectl"
    echo "  sudo mv kubectl /usr/local/bin/"
    exit 1
fi

if ! command -v podman &> /dev/null; then
    print_error "podman is not installed. Please install podman first."
    exit 1
fi

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
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
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
- role: worker
EOF

    kind create cluster --config kind-config.yaml --name $CLUSTER_NAME
    
    # Set kubectl context
    kubectl cluster-info --context kind-$CLUSTER_NAME
}

# Function to setup local registry
setup_registry() {
    print_status "Setting up local registry..."
    
    # Check if registry is already running
    if ! podman ps | grep -q kind-registry; then
        print_status "Starting local registry..."
        podman run -d --name kind-registry --network=kind -p 5001:5000 registry:2
    else
        print_status "Local registry already running"
    fi
    
    # Connect registry to kind network
    if ! podman network exists kind; then
        podman network create kind
    fi
    
    podman network connect kind kind-registry 2>/dev/null || true
}

# Function to build and load images
build_and_load_images() {
    print_status "Building RAGme container images..."
    
    cd ..
    ./scripts/build-containers.sh
    
    print_status "Loading images into kind cluster..."
    
    # Tag images for local registry
    podman tag ragme-api:latest $REGISTRY/ragme-api:$IMAGE_TAG
    podman tag ragme-mcp:latest $REGISTRY/ragme-mcp:$IMAGE_TAG
    podman tag ragme-agent:latest $REGISTRY/ragme-agent:$IMAGE_TAG
    podman tag ragme-frontend:latest $REGISTRY/ragme-frontend:$IMAGE_TAG
    
    # Push to local registry
    podman push $REGISTRY/ragme-api:$IMAGE_TAG
    podman push $REGISTRY/ragme-mcp:$IMAGE_TAG
    podman push $REGISTRY/ragme-agent:$IMAGE_TAG
    podman push $REGISTRY/ragme-frontend:$IMAGE_TAG
    
    cd deployment
}

# Function to deploy services
deploy_services() {
    print_status "Deploying RAGme services to Kubernetes..."
    
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
    "deploy")
        print_header "Starting RAGme deployment to kind cluster"
        
        # Check if cluster exists
        if ! kind get clusters | grep -q "^$CLUSTER_NAME$"; then
            create_cluster
        else
            print_status "Kind cluster '$CLUSTER_NAME' already exists"
        fi
        
        setup_registry
        build_and_load_images
        deploy_services
        show_status
        ;;
        
    "build")
        print_header "Building container images only"
        build_and_load_images
        ;;
        
    "status")
        show_status
        ;;
        
    "destroy")
        print_header "Destroying RAGme deployment"
        kubectl delete namespace ragme --ignore-not-found
        kind delete cluster --name $CLUSTER_NAME
        podman rm -f kind-registry 2>/dev/null || true
        print_status "Deployment destroyed successfully"
        ;;
        
    "cluster")
        create_cluster
        setup_registry
        ;;
        
    *)
        echo "Usage: $0 [deploy|build|status|destroy|cluster]"
        echo ""
        echo "Commands:"
        echo "  deploy    - Full deployment (default): create cluster, build images, deploy services"
        echo "  build     - Build and load container images only"
        echo "  status    - Show deployment status and access URLs"
        echo "  destroy   - Delete the entire deployment and cluster"
        echo "  cluster   - Create kind cluster and registry only"
        echo ""
        echo "Environment variables:"
        echo "  CLUSTER_NAME  - Kind cluster name (default: ragme-cluster)"
        echo "  REGISTRY      - Container registry (default: localhost:5001)"
        echo "  IMAGE_TAG     - Image tag (default: latest)"
        exit 1
        ;;
esac