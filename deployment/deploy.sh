#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max
#
# Master deployment script for RAGme
# This script delegates to platform-specific deployment scripts

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_status() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 <platform> <command> [options]

Platforms:
  kind    - Deploy to local Kind cluster
  gke     - Deploy to Google Kubernetes Engine

Commands:
  deploy     - Deploy RAGme to the specified platform
  destroy    - Destroy RAGme deployment
  status     - Show deployment status
  logs       - Show logs for all services
  build      - Build container images only
  apply      - Apply Kubernetes manifests only
  list       - List available clusters (GKE only)
  create     - Create a new cluster (GKE only)
  help       - Show this help message

Examples:
  $0 kind deploy          # Deploy to Kind cluster
  $0 gke deploy           # Deploy to GKE
  $0 kind destroy         # Destroy Kind deployment
  $0 gke status           # Show GKE deployment status

EOF
}

# Handle help command without arguments
if [ $# -eq 0 ] || [ "$1" = "help" ]; then
    show_usage
    exit 0
fi

# Check if platform and command are provided
if [ $# -lt 2 ]; then
    print_error "Missing required arguments"
    show_usage
    exit 1
fi

PLATFORM="$1"
COMMAND="$2"
shift 2  # Remove platform and command from arguments

# Validate platform
case "$PLATFORM" in
    kind|gke)
        ;;
    *)
        print_error "Invalid platform: $PLATFORM"
        print_info "Valid platforms: kind, gke"
        exit 1
        ;;
esac

# Validate command
case "$COMMAND" in
    deploy|destroy|status|logs|build|apply|list|create|help)
        ;;
    *)
        print_error "Invalid command: $COMMAND"
        print_info "Valid commands: deploy, destroy, status, logs, build, apply, list, create, help"
        exit 1
        ;;
esac

# Handle help command
if [ "$COMMAND" = "help" ]; then
    show_usage
    exit 0
fi

# Determine script path based on platform
SCRIPT_DIR="scripts/$PLATFORM"
SCRIPT_NAME="deploy-$PLATFORM.sh"

# Check if the platform-specific script exists
if [ ! -f "$SCRIPT_DIR/$SCRIPT_NAME" ]; then
    print_error "Platform-specific script not found: $SCRIPT_DIR/$SCRIPT_NAME"
    exit 1
fi

# Make sure the script is executable
chmod +x "$SCRIPT_DIR/$SCRIPT_NAME"

print_header "RAGme Deployment - $PLATFORM"
print_info "Platform: $PLATFORM"
print_info "Command: $COMMAND"
print_info "Script: $SCRIPT_DIR/$SCRIPT_NAME"

# Execute the platform-specific script
exec "$SCRIPT_DIR/$SCRIPT_NAME" "$COMMAND" "$@"
