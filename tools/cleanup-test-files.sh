#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# RAGme Test Files Cleanup Script
# Cleans up test files from storage and vector database

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
API_URL="http://localhost:${RAGME_API_PORT:-8021}"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if we're in the right directory
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/config.yaml" ]]; then
        print_status $RED "❌ Error: config.yaml not found. Please run this script from the RAGme project root."
        exit 1
    fi
}

# Function to clean up storage files
cleanup_storage_files() {
    print_status $BLUE "🧹 Cleaning up test files from storage..."
    
    if command -v python3 >/dev/null 2>&1; then
        # Use Python to clean up storage files
        python3 -c "
import sys
import os
sys.path.insert(0, 'src')
try:
    from ragme.utils.storage import StorageService
    from ragme.utils.config_manager import config
    
    storage_service = StorageService(config)
    
    # List of test file patterns to clean up
    test_patterns = [
        'test_image.png',
        'test_data.bin', 
        'test_url.pdf',
        'cleanup_test.pdf',
        'test_storage.txt',
        'test_document.txt'
    ]
    
    # Also clean up timestamped test files from today
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    test_patterns.extend([
        f'{today}_*_test_*.png',
        f'{today}_*_test_*.pdf',
        f'{today}_*_test_*.txt',
        f'{today}_*_test_*.bin'
    ])
    
    deleted_count = 0
    
    # Get all files from storage
    all_files = storage_service.list_files()
    
    for file_info in all_files:
        file_name = file_info.get('name', '')
        
        # Check if file matches any test pattern
        should_delete = False
        for pattern in test_patterns:
            if pattern in file_name:
                should_delete = True
                break
        
        if should_delete:
            try:
                if storage_service.delete_file(file_name):
                    print(f'  ✅ Deleted test file: {file_name}')
                    deleted_count += 1
                else:
                    print(f'  ⚠️ Failed to delete: {file_name}')
            except Exception as e:
                print(f'  ❌ Error deleting {file_name}: {e}')
    
    if deleted_count > 0:
        print(f'✅ Cleaned up {deleted_count} test files from storage')
    else:
        print('✅ No test files found to clean up')
        
except Exception as e:
    print(f'❌ Error: Failed to cleanup storage files: {e}')
    exit(1)
" 2>/dev/null || {
            print_status $RED "❌ Error: Could not clean up storage files (Python not available)"
            return 1
        }
    else
        print_status $RED "❌ Error: Could not clean up storage files (Python not available)"
        return 1
    fi
}

# Function to clean up test documents from vector database
cleanup_test_documents() {
    print_status $BLUE "🗄️ Cleaning up test documents from vector database..."
    
    # Check if API is available
    if ! curl -s --max-time 5 "$API_URL" > /dev/null 2>&1; then
        print_status $YELLOW "⚠️ Warning: API not available, skipping VDB cleanup"
        return 0
    fi
    
    # Clean up all documents from test collections
    local collections_to_clean=("documents" "images")
    
    for collection_type in "${collections_to_clean[@]}"; do
        print_status $YELLOW "  🧹 Cleaning up $collection_type collection..."
        
        # Get list of documents from API
        local response=$(curl -s --max-time 10 "$API_URL/list-documents?content_type=$collection_type&limit=100" 2>/dev/null || echo "{}")
        
        if echo "$response" | grep -q '"status":"success"'; then
            # Extract document IDs and delete them
            local doc_ids=$(echo "$response" | grep -o '"id":"[^"]*"' | sed 's/"id":"//g' | sed 's/"//g')
            local deleted_count=0
            
            for doc_id in $doc_ids; do
                print_status $YELLOW "    🗑️ Deleting $collection_type: $doc_id"
                local delete_response=$(curl -s --max-time 10 -X DELETE "$API_URL/delete-document/$doc_id" 2>/dev/null || echo "{}")
                
                if echo "$delete_response" | grep -q '"status":"success"'; then
                    print_status $GREEN "      ✅ Successfully deleted $collection_type: $doc_id"
                    ((deleted_count++))
                else
                    print_status $YELLOW "      ⚠️ Failed to delete $collection_type: $doc_id"
                fi
            done
            
            if [ $deleted_count -gt 0 ]; then
                print_status $GREEN "    ✅ Cleaned up $deleted_count $collection_type from test collection"
            else
                print_status $BLUE "    ℹ️ No $collection_type found to clean up"
            fi
        else
            print_status $YELLOW "    ⚠️ Could not retrieve $collection_type for cleanup"
        fi
    done
}

# Function to clean up test files from watch directory
cleanup_watch_directory() {
    print_status $BLUE "📁 Cleaning up test files from watch directory..."
    
    local watch_dir="watch_directory"
    if [ ! -d "$watch_dir" ]; then
        print_status $YELLOW "  ℹ️ Watch directory not found, skipping"
        return 0
    fi
    
    local deleted_count=0
    
    # Remove test files from watch directory
    local test_files=(
        "$watch_dir/test_integration.pdf"
        "$watch_dir/test.pdf"
        "$watch_dir/test_integration_*.pdf"
    )
    
    for test_file in "${test_files[@]}"; do
        if [ -f "$test_file" ]; then
            print_status $YELLOW "  🗑️ Removing test file: $test_file"
            rm -f "$test_file"
            ((deleted_count++))
        fi
        
        # Also check for files with similar names
        for file in "$watch_dir"/test*integration*.pdf "$watch_dir"/test*.pdf; do
            if [ -f "$file" ] && [[ "$file" == *"test"* ]]; then
                print_status $YELLOW "  🗑️ Removing test file: $file"
                rm -f "$file"
                ((deleted_count++))
            fi
        done
    done
    
    if [ $deleted_count -gt 0 ]; then
        print_status $GREEN "  ✅ Cleaned up $deleted_count test files from watch directory"
    else
        print_status $BLUE "  ℹ️ No test files found in watch directory"
    fi
}

# Main function
main() {
    print_status $BLUE "🧹 RAGme Test Files Cleanup"
    print_status $BLUE "=========================="
    
    # Check prerequisites
    check_project_root
    
    # Change to project root for consistent execution
    cd "$PROJECT_ROOT"
    
    # Clean up storage files
    cleanup_storage_files
    
    # Clean up test documents from vector database
    cleanup_test_documents
    
    # Clean up test files from watch directory
    cleanup_watch_directory
    
    print_status $GREEN "✅ Test files cleanup completed successfully!"
}

# Handle help command
if [[ "$1" == "help" ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "RAGme Test Files Cleanup Script"
    echo "==============================="
    echo
    echo "USAGE:"
    echo "  ./tools/cleanup-test-files.sh        # Clean up all test files"
    echo "  ./tools/cleanup-test-files.sh help   # Show this help message"
    echo
    echo "This script cleans up:"
    echo "  - Test files from storage (MinIO/S3/Local)"
    echo "  - Test documents from vector database"
    echo "  - Test files from watch directory"
    echo
    echo "Test file patterns cleaned:"
    echo "  - test_image.png, test_data.bin, test_url.pdf, etc."
    echo "  - Timestamped test files from today"
    echo "  - Files with 'test' in the name"
    echo
    exit 0
fi

# Run main function
main "$@"
