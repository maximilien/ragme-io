#!/bin/bash

# Script to create a new standard GKE cluster for RAGme deployment

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
    echo -e "${BLUE}[GKE-CLUSTER]${NC} $1"
}

# Configuration
PROJECT_ID=${PROJECT_ID:-propane-atrium-471123-u4}
CLUSTER_NAME=${CLUSTER_NAME:-ragme-standard}
ZONE=${ZONE:-us-central1-a}
MACHINE_TYPE=${MACHINE_TYPE:-e2-standard-2}
NUM_NODES=${NUM_NODES:-2}
DISK_SIZE=${DISK_SIZE:-50}
DISK_TYPE=${DISK_TYPE:-pd-standard}

# Function to show help
show_help() {
    echo -e "${BLUE}RAGme GKE Cluster Creation Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  create    - Create a new standard GKE cluster"
    echo "  delete    - Delete the GKE cluster"
    echo "  status    - Show cluster status"
    echo "  help      - Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID    - GCP Project ID (default: propane-atrium-471123-u4)"
    echo "  CLUSTER_NAME  - GKE Cluster name (default: ragme-standard)"
    echo "  ZONE          - GCP Zone (default: us-central1-a)"
    echo "  MACHINE_TYPE  - Machine type (default: e2-standard-2)"
    echo "  NUM_NODES     - Number of nodes (default: 2)"
    echo "  DISK_SIZE     - Disk size in GB (default: 50)"
    echo "  DISK_TYPE     - Disk type (default: pd-standard)"
    echo ""
}

# Function to create cluster
create_cluster() {
    print_header "Creating standard GKE cluster: ${CLUSTER_NAME}"
    
    # Check if cluster already exists
    if gcloud container clusters describe ${CLUSTER_NAME} --zone ${ZONE} --project ${PROJECT_ID} &>/dev/null; then
        print_warning "Cluster ${CLUSTER_NAME} already exists"
        read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            delete_cluster
        else
            print_status "Using existing cluster"
            return 0
        fi
    fi
    
    print_status "Creating cluster with the following configuration:"
    echo "  Project: ${PROJECT_ID}"
    echo "  Cluster: ${CLUSTER_NAME}"
    echo "  Zone: ${ZONE}"
    echo "  Machine Type: ${MACHINE_TYPE}"
    echo "  Nodes: ${NUM_NODES}"
    echo "  Disk Size: ${DISK_SIZE}GB"
    echo "  Disk Type: ${DISK_TYPE}"
    
    # Create the cluster
    gcloud container clusters create ${CLUSTER_NAME} \
        --project=${PROJECT_ID} \
        --zone=${ZONE} \
        --machine-type=${MACHINE_TYPE} \
        --num-nodes=${NUM_NODES} \
        --disk-size=${DISK_SIZE} \
        --disk-type=${DISK_TYPE} \
        --enable-autoscaling \
        --min-nodes=1 \
        --max-nodes=5 \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-ip-alias \
        --network=default \
        --subnetwork=default \
        --enable-network-policy \
        --addons=HttpLoadBalancing,HorizontalPodAutoscaling \
        --enable-stackdriver-kubernetes
    
    print_status "Cluster created successfully!"
    
    # Get credentials
    print_status "Getting cluster credentials..."
    gcloud container clusters get-credentials ${CLUSTER_NAME} \
        --zone ${ZONE} \
        --project ${PROJECT_ID}
    
    # Verify cluster is working
    print_status "Verifying cluster..."
    kubectl get nodes
    
    print_status "Cluster is ready for deployment!"
}

# Function to delete cluster
delete_cluster() {
    print_header "Deleting GKE cluster: ${CLUSTER_NAME}"
    
    print_warning "This will delete the entire cluster and all its resources"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deleting cluster..."
        gcloud container clusters delete ${CLUSTER_NAME} \
            --zone ${ZONE} \
            --project ${PROJECT_ID} \
            --quiet
        
        print_status "Cluster deleted successfully!"
    else
        print_status "Cluster deletion cancelled"
    fi
}

# Function to show cluster status
show_status() {
    print_header "Cluster Status"
    
    if gcloud container clusters describe ${CLUSTER_NAME} --zone ${ZONE} --project ${PROJECT_ID} &>/dev/null; then
        print_status "Cluster exists and is accessible"
        
        # Get credentials
        gcloud container clusters get-credentials ${CLUSTER_NAME} \
            --zone ${ZONE} \
            --project ${PROJECT_ID} &>/dev/null
        
        echo ""
        print_status "Nodes:"
        kubectl get nodes
        
        echo ""
        print_status "Cluster info:"
        kubectl cluster-info
    else
        print_warning "Cluster does not exist or is not accessible"
    fi
}

# Main script logic
main() {
    case "${1:-help}" in
        "create")
            create_cluster
            ;;
        "delete")
            delete_cluster
            ;;
        "status")
            show_status
            ;;
        "help")
            show_help
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
