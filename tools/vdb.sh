#!/bin/bash

# RAGme VDB Management Tool
# Direct management of vector database collections using the existing VDB abstractions

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

# Python script path
PYTHON_SCRIPT="$PROJECT_ROOT/src/ragme/vdbs/vdb_management.py"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if Python script exists
check_python_script() {
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        print_status $RED "❌ Error: Python management script not found: $PYTHON_SCRIPT"
        exit 1
    fi
}

# Function to check if we're in the right directory
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/config.yaml" ]]; then
        print_status $RED "❌ Error: config.yaml not found. Please run this script from the RAGme project root."
        exit 1
    fi
}

# Function to check Python dependencies
check_dependencies() {
    if ! python3 -c "import sys; sys.path.insert(0, '$PROJECT_ROOT/src'); from ragme.utils.config_manager import config; print('✅ Dependencies OK')" 2>/dev/null; then
        print_status $YELLOW "⚠️  Warning: Some Python dependencies may not be available"
        print_status $YELLOW "   Make sure you have installed the RAGme requirements: pip install -r requirements.txt"
    fi
}

# Main execution
main() {
    # Check prerequisites
    check_project_root
    check_python_script
    check_dependencies
    
    # Change to project root for consistent execution
    cd "$PROJECT_ROOT"
    
    # Execute the Python script as a module using uv run
    uv run --active python3 -m ragme.vdbs.vdb_management "$@"
}

# Handle help command specially for better formatting
if [[ "$1" == "help" ]] || [[ $# -eq 0 ]]; then
    print_status $BLUE "RAGme VDB Management Tool"
    print_status $BLUE "========================"
    echo
    print_status $GREEN "USAGE:"
    echo "  ./tools/vdb.sh help                         # shows help for this script"
    echo "  ./tools/vdb.sh --show                       # shows currently configured VDB"
    echo "  ./tools/vdb.sh health                       # attempts to connect to VDB and collections"
    echo "  ./tools/vdb.sh virtual-structure            # shows virtual structure (chunks, grouped images, documents, individual images)"
    echo "  ./tools/vdb.sh document-groups              # shows how documents are grouped into chunks"
    echo "  ./tools/vdb.sh image-groups                 # shows how images are grouped by PDF source"
    echo "  ./tools/vdb.sh delete-document <filename>   # delete document and all its chunks and extracted images"
    echo "  ./tools/vdb.sh collections --list           # shows collection names"
    echo "  ./tools/vdb.sh collections --text --list    # list docs in text collection (shows source, type, text preview)"
    echo "  ./tools/vdb.sh collections --image --list   # list docs in image collection (shows source, classification, image data)"
    echo "  ./tools/vdb.sh collections --text --delete  # delete the text collection content"
    echo "  ./tools/vdb.sh collections --image --delete # delete the image collection content"
    echo
    print_status $YELLOW "EXAMPLES:"
    echo "  ./tools/vdb.sh --show                       # Check current VDB configuration"
    echo "  ./tools/vdb.sh health                       # Test VDB connectivity"
    echo "  ./tools/vdb.sh virtual-structure            # View virtual structure overview"
    echo "  ./tools/vdb.sh document-groups              # See how documents are chunked"
    echo "  ./tools/vdb.sh image-groups                 # See how images are grouped by PDF"
    echo "  ./tools/vdb.sh delete-document ragme-io.pdf # Delete document and all its chunks/images"
    echo "  ./tools/vdb.sh collections --text --list    # List all text documents"
    echo "  ./tools/vdb.sh collections --image --delete # Clear all image documents"
    echo
    print_status $YELLOW "NOTES:"
    echo "  - This tool uses the same configuration as RAGme (config.yaml + .env)"
    echo "  - Destructive operations (--delete) require confirmation"
    echo "  - The tool works independently of RAGme services"
    echo "  - Use this for administrative tasks and cleanup operations"
    exit 0
fi

# Run main function
main "$@"
