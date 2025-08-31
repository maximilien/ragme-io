#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# Recovery script for RAGme collections
# This script helps recover collections by re-indexing existing document files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --reindex-documents    Re-index all documents in storage"
    echo "  --reindex-images       Re-index all images in storage"
    echo "  --reindex-all          Re-index both documents and images"
    echo "  --check-status         Check current collection status"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --check-status      # Check what's in your collections"
    echo "  $0 --reindex-all       # Re-index all content"
    echo "  $0 --reindex-documents # Re-index only documents"
}

# Function to check collection status
check_status() {
    print_header "Checking Collection Status"
    
    print_status "Checking text collection..."
    ./tools/vdb.sh collections --text --list
    
    echo ""
    print_status "Checking image collection..."
    ./tools/vdb.sh collections --image --list
    
    echo ""
    print_status "Checking storage files..."
    echo "Documents in storage:"
    ls -la minio_data/documents/ 2>/dev/null | grep -v "^total" | wc -l | tr -d ' '
    echo "Images in storage:"
    ls -la minio_data/images/ 2>/dev/null | grep -v "^total" | wc -l | tr -d ' '
}

# Function to re-index documents
reindex_documents() {
    print_header "Re-indexing Documents"
    
    print_status "Finding document files in storage..."
    doc_files=$(find minio_data/documents/ -name "*.pdf" -o -name "*.txt" -o -name "*.md" 2>/dev/null | head -10)
    
    if [ -z "$doc_files" ]; then
        print_warning "No document files found in storage"
        return 1
    fi
    
    print_status "Found document files:"
    echo "$doc_files"
    
    print_status "Starting re-indexing process..."
    print_warning "This will add all documents back to your collection"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Re-indexing cancelled"
        return 1
    fi
    
    # Start the API if not running
    if ! curl -s --max-time 5 http://localhost:8021/health > /dev/null 2>&1; then
        print_status "Starting RAGme API..."
        ./start.sh > /dev/null 2>&1 &
        sleep 5
    fi
    
    # Re-index each document
    for doc_file in $doc_files; do
        print_status "Re-indexing: $(basename "$doc_file")"
        
        # Use the API to add the document
        if [[ "$doc_file" == *.pdf ]]; then
            # For PDFs, we need to use the MCP server
            response=$(curl -s -X POST "http://localhost:8022/tool/process_pdf" \
                -H "Content-Type: application/json" \
                -d "{\"file_path\": \"$doc_file\"}")
            
            if echo "$response" | grep -q "success"; then
                print_success "Added PDF: $(basename "$doc_file")"
            else
                print_error "Failed to add PDF: $(basename "$doc_file")"
            fi
        else
            # For other files, we can use the API directly
            response=$(curl -s -X POST "http://localhost:8021/add-document" \
                -F "file=@$doc_file")
            
            if echo "$response" | grep -q "success"; then
                print_success "Added document: $(basename "$doc_file")"
            else
                print_error "Failed to add document: $(basename "$doc_file")"
            fi
        fi
    done
    
    print_success "Document re-indexing completed!"
}

# Function to re-index images
reindex_images() {
    print_header "Re-indexing Images"
    
    print_status "Finding image files in storage..."
    image_files=$(find minio_data/images/ -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" 2>/dev/null | head -10)
    
    if [ -z "$image_files" ]; then
        print_warning "No image files found in storage"
        return 1
    fi
    
    print_status "Found image files:"
    echo "$image_files"
    
    print_status "Starting re-indexing process..."
    print_warning "This will add all images back to your collection"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Re-indexing cancelled"
        return 1
    fi
    
    # Start the API if not running
    if ! curl -s --max-time 5 http://localhost:8021/health > /dev/null 2>&1; then
        print_status "Starting RAGme API..."
        ./start.sh > /dev/null 2>&1 &
        sleep 5
    fi
    
    # Re-index each image
    for image_file in $image_files; do
        print_status "Re-indexing: $(basename "$image_file")"
        
        # Use the API to add the image
        response=$(curl -s -X POST "http://localhost:8021/add-image" \
            -F "file=@$image_file")
        
        if echo "$response" | grep -q "success"; then
            print_success "Added image: $(basename "$image_file")"
        else
            print_error "Failed to add image: $(basename "$image_file")"
        fi
    done
    
    print_success "Image re-indexing completed!"
}

# Main script logic
main() {
    local check_status_flag=false
    local reindex_documents_flag=false
    local reindex_images_flag=false
    local reindex_all_flag=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-status)
                check_status_flag=true
                shift
                ;;
            --reindex-documents)
                reindex_documents_flag=true
                shift
                ;;
            --reindex-images)
                reindex_images_flag=true
                shift
                ;;
            --reindex-all)
                reindex_all_flag=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Default to check status if no options provided
    if [[ "$check_status_flag" == false && "$reindex_documents_flag" == false && "$reindex_images_flag" == false && "$reindex_all_flag" == false ]]; then
        check_status_flag=true
    fi
    
    print_header "RAGme Collection Recovery Tool"
    
    # Check if we're in the right directory
    if [[ ! -f "config.yaml" ]]; then
        print_error "Please run this script from the RAGme project root directory"
        exit 1
    fi
    
    # Execute requested operations
    if [[ "$check_status_flag" == true ]]; then
        check_status
    fi
    
    if [[ "$reindex_all_flag" == true ]]; then
        reindex_documents
        reindex_images
    else
        if [[ "$reindex_documents_flag" == true ]]; then
            reindex_documents
        fi
        
        if [[ "$reindex_images_flag" == true ]]; then
            reindex_images
        fi
    fi
    
    print_header "Recovery Process Completed"
    print_status "Run '$0 --check-status' to verify your collections"
}

# Run main function with all arguments
main "$@"
