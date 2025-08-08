#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# Integration test runner for RAGme AI Agents and APIs
# This script runs comprehensive integration tests for both APIs and Agents levels

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

# Function to check if services are running
check_services() {
    print_status "Checking if RAGme services are running..."
    
    # Check API service
    if curl -s --max-time 10 http://localhost:8021/config > /dev/null 2>&1; then
        print_success "API service is running on port 8021"
    else
        print_error "API service is not running on port 8021"
        return 1
    fi
    
    # Check MCP service
    if curl -s --max-time 10 http://localhost:8022/tool/process_pdf > /dev/null 2>&1; then
        print_success "MCP service is running on port 8022"
    else
        print_error "MCP service is not running on port 8022"
        return 1
    fi
    
    return 0
}

# Function to check API keys for integration tests
check_api_keys() {
    print_status "Checking API keys for integration tests..."
    
    # Load environment variables from .env file if it exists
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env file..."
        export $(grep -v '^#' .env | xargs)
    fi
    
    # Check for OpenAI API key
    if [ -z "$OPENAI_API_KEY" ] || [[ "$OPENAI_API_KEY" == fake-* ]] || [[ "$OPENAI_API_KEY" == "your-openai-api-key-here" ]]; then
        print_warning "No valid OpenAI API key found in environment"
        print_warning "Integration tests may fail without a real OpenAI API key"
        return 1
    fi
    
    print_success "OpenAI API key found"
    
    # Check vector database configuration
    VECTOR_DB_TYPE=${VECTOR_DB_TYPE:-"weaviate-local"}
    print_status "Vector database type: $VECTOR_DB_TYPE"
    
    if [ "$VECTOR_DB_TYPE" = "weaviate" ]; then
        if [ -z "$WEAVIATE_API_KEY" ] || [[ "$WEAVIATE_API_KEY" == fake-* ]] || [[ "$WEAVIATE_API_KEY" == "your-weaviate-api-key-here" ]]; then
            print_warning "No valid Weaviate API key found"
            print_warning "Integration tests may fail without a real Weaviate API key"
            return 1
        fi
        if [ -z "$WEAVIATE_URL" ] || [[ "$WEAVIATE_URL" == fake-* ]]; then
            print_warning "No valid Weaviate URL found"
            print_warning "Integration tests may fail without a real Weaviate URL"
            return 1
        fi
        print_success "Weaviate API key and URL found"
    elif [ "$VECTOR_DB_TYPE" = "weaviate-local" ]; then
        print_success "Using local Weaviate (no API key required)"
    elif [ "$VECTOR_DB_TYPE" = "milvus" ]; then
        if [ -z "$MILVUS_URI" ]; then
            print_warning "No Milvus URI found"
            print_warning "Integration tests may fail without a Milvus URI"
            return 1
        fi
        print_success "Milvus URI found"
    fi
    
    return 0
}

# Function to stop services
stop_services() {
    print_status "Stopping RAGme services..."
    ./stop.sh
}

# Function to start services
start_services() {
    print_status "Starting RAGme services..."
    ./start.sh
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check if services are running
    if ! check_services; then
        print_error "Failed to start services properly"
        exit 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    local test_type="$1"
    
    print_status "Running $test_type integration tests..."
    
    # Run the integration test runner
    if python tests/integration/run_integration_tests.py --$test_type; then
        print_success "$test_type integration tests passed!"
        return 0
    else
        print_error "$test_type integration tests failed!"
        return 1
    fi
}

# Function to run all integration tests
run_all_integration_tests() {
    print_status "Running all integration tests..."
    
    # Run the integration test runner
    if python tests/integration/run_integration_tests.py --all; then
        print_success "All integration tests passed!"
        return 0
    else
        print_error "Some integration tests failed!"
        return 1
    fi
}

# Function to run tests with pytest
run_pytest_tests() {
    local test_type="$1"
    
    print_status "Running $test_type integration tests with pytest..."
    
    if python tests/integration/run_integration_tests.py --$test_type --pytest; then
        print_success "$test_type pytest integration tests passed!"
        return 0
    else
        print_error "$test_type pytest integration tests failed!"
        return 1
    fi
}

# Function to cleanup test configuration
cleanup_test_config() {
    print_status "Cleaning up test configuration..."
    
    # Check if there's a backup config file
    if [ -f "config.yaml.test_backup" ]; then
        print_status "Restoring original config.yaml from backup..."
        if cp config.yaml.test_backup config.yaml; then
            print_success "Configuration restored successfully"
            rm -f config.yaml.test_backup config.yaml.test_temp
        else
            print_error "Failed to restore configuration"
            return 1
        fi
    else
        print_warning "No backup configuration found"
    fi
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --api              Run API integration tests only"
    echo "  --agents           Run Agent integration tests only"
    echo "  --all              Run all integration tests (default)"
    echo "  --pytest           Use pytest framework for running tests"
    echo "  --stop-first       Stop services before running tests"
    echo "  --start-services   Start services before running tests"
    echo "  --cleanup          Stop services after running tests"
    echo "  --cleanup-config   Clean up test configuration files"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --api                    # Run API tests only"
    echo "  $0 --agents --pytest        # Run Agent tests with pytest"
    echo "  $0 --all --stop-first       # Stop services, run all tests"
    echo "  $0 --start-services --all   # Start services, run all tests"
    echo "  $0 --cleanup-config         # Clean up test configuration files"
}

# Main script logic
main() {
    local run_api=false
    local run_agents=false
    local run_all=true
    local use_pytest=false
    local stop_first=false
    local start_services_flag=false
    local cleanup=false
    local cleanup_config=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --api)
                run_api=true
                run_all=false
                shift
                ;;
            --agents)
                run_agents=true
                run_all=false
                shift
                ;;
            --all)
                run_all=true
                shift
                ;;
            --pytest)
                use_pytest=true
                shift
                ;;
            --stop-first)
                stop_first=true
                shift
                ;;
            --start-services)
                start_services_flag=true
                shift
                ;;
            --cleanup)
                cleanup=true
                shift
                ;;
            --cleanup-config)
                cleanup_config=true
                shift
                ;;
            --help)
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
    
    print_status "RAGme AI Integration Test Runner"
    echo "========================================"
    
    # Handle cleanup-config option
    if [ "$cleanup_config" = true ]; then
        cleanup_test_config
        exit 0
    fi
    
    # Stop services first if requested
    if [ "$stop_first" = true ]; then
        stop_services
    fi
    
    # Start services if requested
    if [ "$start_services_flag" = true ]; then
        start_services
    fi
    
    # Check if services are running
    if ! check_services; then
        print_warning "Services are not running. Please start them first:"
        print_warning "  ./start.sh"
        print_warning "Or use --start-services flag to start them automatically."
        exit 1
    fi
    
    # Check API keys for integration tests
    if ! check_api_keys; then
        print_warning "API key validation failed. Integration tests may fail."
        print_warning "You can continue anyway, but tests may not work properly."
        read -p "Continue with integration tests? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Aborting integration tests"
            exit 1
        fi
    fi
    
    # Run tests based on options
    local success=true
    
    if [ "$use_pytest" = true ]; then
        if [ "$run_api" = true ] || [ "$run_all" = true ]; then
            if ! run_pytest_tests "api"; then
                success=false
            fi
        fi
        
        if [ "$run_agents" = true ] || [ "$run_all" = true ]; then
            if ! run_pytest_tests "agents"; then
                success=false
            fi
        fi
    else
        if [ "$run_api" = true ] || [ "$run_all" = true ]; then
            if ! run_integration_tests "api"; then
                success=false
            fi
        fi
        
        if [ "$run_agents" = true ] || [ "$run_all" = true ]; then
            if ! run_integration_tests "agents"; then
                success=false
            fi
        fi
    fi
    
    # Cleanup if requested
    if [ "$cleanup" = true ]; then
        stop_services
    fi
    
    # Print final result
    echo ""
    echo "========================================"
    if [ "$success" = true ]; then
        print_success "All integration tests completed successfully!"
        exit 0
    else
        print_error "Some integration tests failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
