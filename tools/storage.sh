#!/bin/bash

# RAGme Storage Management Tool
# Direct management of storage content using the existing storage service

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
PYTHON_SCRIPT="$PROJECT_ROOT/src/ragme/utils/storage_management.py"

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
    
    # Execute the Python script as a module with the correct Python path
    PYTHONPATH=src python3 -m ragme.utils.storage_management "$@"
}

# Handle help command specially for better formatting
if [[ "$1" == "help" ]] || [[ $# -eq 0 ]]; then
    print_status $BLUE "RAGme Storage Management Tool"
    print_status $BLUE "============================"
    echo
    print_status $GREEN "USAGE:"
    echo "  ./tools/storage.sh help                        # shows help for this script"
    echo "  ./tools/storage.sh info                        # shows storage configuration and status"
    echo "  ./tools/storage.sh health                      # checks storage service health and connectivity"
    echo "  ./tools/storage.sh health --verbose            # checks health with verbose output"
    echo "  ./tools/storage.sh buckets                     # lists all available buckets"
    echo "  ./tools/storage.sh buckets --details           # lists buckets with detailed information"
    echo "  ./tools/storage.sh list                        # lists all files in storage"
    echo "  ./tools/storage.sh list --details              # lists files with detailed information"
    echo "  ./tools/storage.sh list --prefix \"documents/\"  # lists files with specific prefix"
    echo "  ./tools/storage.sh list --all                  # lists files from all buckets"
    echo "  ./tools/storage.sh list --bucket <name>        # lists files from specific bucket"
    echo "  ./tools/storage.sh links                       # shows download links for all files"
    echo "  ./tools/storage.sh links document.pdf          # shows download link for specific file"
    echo "  ./tools/storage.sh delete document.pdf         # deletes specific file (with confirmation)"
    echo "  ./tools/storage.sh delete document.pdf --force # deletes specific file without confirmation"
    echo "  ./tools/storage.sh delete document.pdf --bucket <name> # deletes file from specific bucket"
    echo "  ./tools/storage.sh delete-all                  # deletes all files (with confirmation)"
    echo "  ./tools/storage.sh delete-all --force          # deletes all files without confirmation"
    echo "  ./tools/storage.sh delete-all --prefix \"temp/\" # deletes files with specific prefix"
    echo "  ./tools/storage.sh delete-all --bucket <name>  # deletes all files from specific bucket"
    echo "  ./tools/storage.sh delete-all --all            # deletes all files from all buckets"
    echo
    print_status $YELLOW "EXAMPLES:"
    echo "  ./tools/storage.sh health                      # Check storage service health and connectivity"
    echo "  ./tools/storage.sh buckets                     # List all available buckets"
    echo "  ./tools/storage.sh info                        # Check storage configuration and status"
    echo "  ./tools/storage.sh list --details              # List all files with size and date info"
    echo "  ./tools/storage.sh list --all                  # List files from all buckets"
    echo "  ./tools/storage.sh list --bucket documents     # List files from specific bucket"
    echo "  ./tools/storage.sh links document.pdf          # Get download link for specific file"
    echo "  ./tools/storage.sh delete document.pdf         # Delete specific file with confirmation"
    echo "  ./tools/storage.sh delete-all                  # Clear all storage content with confirmation"
    echo
    print_status $YELLOW "NOTES:"
    echo "  - This tool uses the same configuration as RAGme (config.yaml + .env)"
    echo "  - Destructive operations (delete, delete-all) require confirmation unless --force is used"
    echo "  - The tool works independently of RAGme services"
    echo "  - Use this for administrative tasks and cleanup operations"
    echo "  - Make sure your storage service (MinIO/S3) is running before using this tool"
    exit 0
fi

# Run main function
main "$@"
