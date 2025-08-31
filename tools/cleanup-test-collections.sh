#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# Test Collection Cleanup Tool
# This script cleans up test collections (test_integration and test_integration_images)
# to ensure they are empty before running integration tests.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[CLEANUP]${NC} $1"
}

print_help() {
    echo -e "${BLUE}RAGme Test Collection Cleanup Tool${NC}"
    echo ""
    echo "Usage: ./tools/cleanup-test-collections.sh [OPTIONS]"
    echo ""
    echo "This script cleans up test collections to ensure they are empty."
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --force, -f    Force cleanup without confirmation"
    echo ""
    echo "Test Collections:"
    echo "  - test_integration (text documents)"
    echo "  - test_integration_images (images)"
    echo ""
    echo "Examples:"
    echo "  ./tools/cleanup-test-collections.sh           # Clean with confirmation"
    echo "  ./tools/cleanup-test-collections.sh --force   # Clean without confirmation"
    echo ""
}

# Configuration
TEST_COLLECTION_NAME="test_integration"
TEST_IMAGE_COLLECTION_NAME="test_integration_images"

# Function to check if we're in the right directory
check_project_root() {
    if [[ ! -f "config.yaml" ]]; then
        print_error "❌ config.yaml not found. Please run this script from the RAGme project root."
        exit 1
    fi
}

# Function to confirm cleanup
confirm_cleanup() {
    if [[ "$1" == "--force" ]] || [[ "$1" == "-f" ]]; then
        return 0
    fi
    
    echo -e "\n${YELLOW}⚠️  WARNING: This will delete ALL content from test collections!${NC}"
    echo -e "Collections to clean:"
    echo -e "  - ${TEST_COLLECTION_NAME} (text documents)"
    echo -e "  - ${TEST_IMAGE_COLLECTION_NAME} (images)"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleanup cancelled"
        exit 0
    fi
}

# Function to cleanup test collections
cleanup_test_collections() {
    print_header "Cleaning up test collections..."
    
    # Check if Python script exists
    if [[ ! -f "src/ragme/vdbs/vdb_management.py" ]]; then
        print_error "❌ VDB management script not found: src/ragme/vdbs/vdb_management.py"
        exit 1
    fi
    
    # Use the vdb.sh tool to clean up collections
    print_status "Cleaning up text collection: ${TEST_COLLECTION_NAME}"
    if ./tools/vdb.sh collections --text --delete; then
        print_status "✅ Text collection cleaned up successfully"
    else
        print_warning "⚠️ Text collection cleanup had issues"
    fi
    
    print_status "Cleaning up image collection: ${TEST_IMAGE_COLLECTION_NAME}"
    if ./tools/vdb.sh collections --image --delete; then
        print_status "✅ Image collection cleaned up successfully"
    else
        print_warning "⚠️ Image collection cleanup had issues"
    fi
    
    print_status "✅ Test collections cleanup completed"
}

# Main execution
main() {
    local force_flag=$1
    
    # Check if help is requested
    if [[ "$force_flag" == "--help" ]] || [[ "$force_flag" == "-h" ]] || [[ $# -eq 0 ]]; then
        print_help
        exit 0
    fi
    
    # Check prerequisites
    check_project_root
    
    # Confirm cleanup
    confirm_cleanup "$force_flag"
    
    # Perform cleanup
    cleanup_test_collections
    
    print_header "🎉 Test collections cleanup completed successfully!"
    print_status "You can now run integration tests with clean collections"
}

# Run main function with all arguments
main "$@"
