#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max
#
# RAGme Document Processing Pipeline
# 
# This script provides a command-line interface to the RAGme document processing pipeline.
# It processes PDFs, DOCX files, and images in batch mode with parallel processing,
# comprehensive error handling, and detailed reporting.

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_MODULE="src.ragme.data_processing.pipeline"

# Default values
DEFAULT_BATCH_SIZE=3
DEFAULT_RETRY_LIMIT=3
DEFAULT_VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Function to print help
print_help() {
    cat << EOF
🚀 RAGme Document Processing Pipeline

USAGE:
    $0 <directory> [options]

DESCRIPTION:
    Process documents (PDFs, DOCX) and images in batch mode for RAGme vector database.
    Supports parallel processing, automatic retry logic, progress tracking, and 
    comprehensive reporting with CSV output and individual .processed files.

ARGUMENTS:
    <directory>         Directory containing files to process (required)

OPTIONS:
    -b, --batch-size <n>     Number of parallel processing workers (default: $DEFAULT_BATCH_SIZE)
    -r, --retry-limit <n>    Maximum retry attempts per file (default: $DEFAULT_RETRY_LIMIT)
    -v, --verbose           Enable verbose progress reporting (default: false)
    -h, --help              Show this help message

SUPPORTED FILE TYPES:
    Documents: PDF (.pdf), Microsoft Word (.docx)
    Images:    JPEG (.jpg, .jpeg), PNG (.png), GIF (.gif), WebP (.webp),
               BMP (.bmp), HEIC (.heic, .heif), TIFF (.tiff, .tif)

FEATURES:
    ✅ Parallel processing with configurable batch size
    ✅ Automatic retry logic with configurable limits  
    ✅ Progress tracking and status reporting
    ✅ PDF image extraction and processing
    ✅ EXIF metadata extraction for images
    ✅ AI-powered image classification
    ✅ OCR text extraction from images
    ✅ Text chunking with smart boundary detection
    ✅ Vector database storage (text and image collections)
    ✅ Comprehensive error handling and logging
    ✅ Skip already processed files (.processed marker files)
    ✅ CSV reporting with processing statistics
    ✅ Lock files to prevent concurrent processing

EXAMPLES:
    # Process all files in ./documents directory with default settings
    $0 ./documents

    # Process with high parallelism and verbose output
    $0 ./documents --batch-size 8 --verbose

    # Process with custom retry limit
    $0 ./documents --retry-limit 5 --batch-size 2

OUTPUT:
    - Individual .processed files for each processed document
    - processing_results.csv with comprehensive statistics
    - Console summary with timing and error information

REQUIREMENTS:
    - RAGme system properly configured (config.yaml and .env)
    - Vector database accessible and configured
    - Required Python dependencies installed
    - Sufficient disk space for temporary files during processing

EOF
}

# Function to validate directory
validate_directory() {
    local dir=$1
    
    if [[ ! -d "$dir" ]]; then
        print_color $RED "❌ Error: Directory '$dir' does not exist."
        exit 1
    fi
    
    if [[ ! -r "$dir" ]]; then
        print_color $RED "❌ Error: Directory '$dir' is not readable."
        exit 1
    fi
    
    # Count supported files
    local file_count
    file_count=$(find "$dir" -maxdepth 1 -type f \( \
        -iname "*.pdf" -o \
        -iname "*.docx" -o \
        -iname "*.jpg" -o \
        -iname "*.jpeg" -o \
        -iname "*.png" -o \
        -iname "*.gif" -o \
        -iname "*.webp" -o \
        -iname "*.bmp" -o \
        -iname "*.heic" -o \
        -iname "*.heif" -o \
        -iname "*.tiff" -o \
        -iname "*.tif" \
    \) | wc -l)
    
    if [[ $file_count -eq 0 ]]; then
        print_color $YELLOW "⚠️  Warning: No supported files found in '$dir'"
        print_color $YELLOW "   Supported types: PDF, DOCX, JPG, PNG, GIF, WebP, BMP, HEIC, TIFF"
    fi
    
    echo $file_count
}

# Function to validate numeric parameter
validate_number() {
    local value=$1
    local param_name=$2
    local min_value=${3:-1}
    
    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
        print_color $RED "❌ Error: $param_name must be a positive integer, got: $value"
        exit 1
    fi
    
    if [[ $value -lt $min_value ]]; then
        print_color $RED "❌ Error: $param_name must be at least $min_value, got: $value"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_color $BLUE "🔍 Checking prerequisites..."
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/config.yaml" ]]; then
        print_color $RED "❌ Error: config.yaml not found. Please run this script from the RAGme project root."
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        print_color $YELLOW "⚠️  Warning: .env file not found. Make sure environment variables are set."
    fi
    
    # Check if Python module exists
    if [[ ! -f "$PROJECT_ROOT/src/ragme/data_processing/__init__.py" ]]; then
        print_color $RED "❌ Error: RAGme data processing module not found."
        exit 1
    fi
    
    # Test Python import
    cd "$PROJECT_ROOT"
    if ! python -c "from src.ragme.data_processing import DocumentProcessingPipeline" 2>/dev/null; then
        print_color $RED "❌ Error: Cannot import RAGme data processing pipeline."
        print_color $RED "   Make sure all dependencies are installed: pip install -r requirements.txt"
        exit 1
    fi
    
    print_color $GREEN "✅ Prerequisites check passed"
}

# Function to run the processing pipeline
run_pipeline() {
    local directory=$1
    local batch_size=$2
    local retry_limit=$3
    local verbose=$4
    
    print_color $PURPLE "🚀 Starting RAGme Document Processing Pipeline"
    print_color $CYAN "📁 Directory: $directory"
    print_color $CYAN "⚡ Batch Size: $batch_size workers"
    print_color $CYAN "🔄 Retry Limit: $retry_limit attempts"
    print_color $CYAN "📢 Verbose: $verbose"
    echo
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Create Python script to run the pipeline
    local python_script=$(cat << EOF
import sys
import os
sys.path.insert(0, os.getcwd())

from src.ragme.data_processing.pipeline import DocumentProcessingPipeline

def main():
    try:
        with DocumentProcessingPipeline(
            input_directory="$directory",
            batch_size=$batch_size,
            retry_limit=$retry_limit,
            verbose=$verbose
        ) as pipeline:
            stats = pipeline.run()
            
            # Exit with appropriate code
            if stats['failed_files'] > 0:
                sys.exit(1)  # Some files failed
            else:
                sys.exit(0)  # All files processed successfully
                
    except KeyboardInterrupt:
        print("\n🚨 Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF
    )
    
    # Run the Python pipeline
    echo "$python_script" | python
}

# Main function
main() {
    local directory=""
    local batch_size=$DEFAULT_BATCH_SIZE
    local retry_limit=$DEFAULT_RETRY_LIMIT
    local verbose=$DEFAULT_VERBOSE
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_help
                exit 0
                ;;
            -b|--batch-size)
                batch_size="$2"
                validate_number "$batch_size" "batch-size" 1
                shift 2
                ;;
            -r|--retry-limit)
                retry_limit="$2"
                validate_number "$retry_limit" "retry-limit" 0
                shift 2
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -*)
                print_color $RED "❌ Error: Unknown option $1"
                print_help
                exit 1
                ;;
            *)
                if [[ -z "$directory" ]]; then
                    directory="$1"
                else
                    print_color $RED "❌ Error: Multiple directories specified. Only one directory is supported."
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "$directory" ]]; then
        print_color $RED "❌ Error: Directory argument is required."
        echo
        print_help
        exit 1
    fi
    
    # Validate directory and count files
    local file_count
    file_count=$(validate_directory "$directory")
    
    # Show file discovery results
    if [[ $file_count -gt 0 ]]; then
        print_color $GREEN "✅ Found $file_count supported files in '$directory'"
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Run the pipeline
    run_pipeline "$directory" "$batch_size" "$retry_limit" "$verbose"
}

# Run main function with all arguments
main "$@"