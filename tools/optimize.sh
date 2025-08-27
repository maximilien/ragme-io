#!/bin/bash

# RAGme.io Optimization Tools
# Usage: ./tools/optimize.sh [command] [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

show_help() {
    cat << EOF
RAGme.io Optimization Tools

Usage: $0 [command] [options]

Commands:
    query-threshold [min] [max]    Optimize text relevance threshold using binary search
                                   Default range: 0.2 to 0.8
                                   Stops when precision is within 0.05
    help                           Show this help message

Examples:
    $0 query-threshold              # Use default range 0.2-0.8
    $0 query-threshold 0.1 0.9     # Use custom range 0.1-0.9

Requirements:
    - RAGme backend must be running
    - Documents must be indexed (ragme-io.pdf and maximilien.org)
    - Python environment must be activated

EOF
}

optimize_query_threshold() {
    local min_threshold=${1:-0.2}
    local max_threshold=${2:-0.8}
    
    echo "🔍 Starting query threshold optimization..."
    echo "Range: $min_threshold to $max_threshold"
    echo "Precision: 0.05"
    echo ""
    
    # Check if backend is running
    if ! curl -s http://localhost:8021/health > /dev/null 2>&1; then
        echo "❌ Error: RAGme backend is not running on localhost:8021"
        echo "Please start the backend with: ./start.sh"
        exit 1
    fi
    
    # Run the optimization script
    cd "$PROJECT_ROOT"
    python tools/threshold_optimizer.py "$min_threshold" "$max_threshold"
}

case "${1:-help}" in
    "query-threshold")
        optimize_query_threshold "$2" "$3"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
