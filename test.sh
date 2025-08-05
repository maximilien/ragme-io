#!/bin/bash

# RAGme AI Test Suite

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
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_help() {
    echo -e "${BLUE}RAGme AI Test Suite${NC}"
    echo ""
    echo "Usage: ./test.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  unit        Run only unit tests (Python pytest)"
    echo "  api         Run only API tests (FastAPI endpoints)"
    echo "  mcp         Run only MCP server tests (Model Context Protocol)"
    echo "  integration Run only integration tests (end-to-end system tests)"
    echo "  all         Run all tests (unit + api + mcp + integration)"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./test.sh unit         # Run only unit tests"
    echo "  ./test.sh api          # Run only API tests"
    echo "  ./test.sh mcp          # Run only MCP server tests"
    echo "  ./test.sh integration  # Run only integration tests"
    echo "  ./test.sh all          # Run all tests"
    echo "  ./test.sh              # Run unit tests (default)"
    echo ""
    echo "Test Categories:"
    echo "  Unit Tests:"
    echo "    - Python unit tests for core functionality"
    echo "    - Vector database implementations"
    echo "    - Agent functionality"
    echo "    - Common utilities"
    echo ""
    echo "  API Tests:"
    echo "    - FastAPI endpoint testing"
    echo "    - API response validation"
    echo "    - Request/response handling"
    echo ""
    echo "  MCP Tests:"
    echo "    - Model Context Protocol server tests"
    echo "    - MCP endpoint validation"
    echo "    - Protocol compliance"
    echo ""
    echo "  Integration Tests:"
    echo "    - End-to-end system testing"
    echo "    - Service communication"
    echo "    - Complete workflow validation"
    echo "    - File monitoring and processing"
}

# Check command line arguments
case "${1:-unit}" in
    "unit")
        RUN_UNIT_TESTS=true
        RUN_API_TESTS=false
        RUN_MCP_TESTS=false
        RUN_INTEGRATION_TESTS=false
        ;;
    "api")
        RUN_UNIT_TESTS=false
        RUN_API_TESTS=true
        RUN_MCP_TESTS=false
        RUN_INTEGRATION_TESTS=false
        ;;
    "mcp")
        RUN_UNIT_TESTS=false
        RUN_API_TESTS=false
        RUN_MCP_TESTS=true
        RUN_INTEGRATION_TESTS=false
        ;;
    "integration")
        RUN_UNIT_TESTS=false
        RUN_API_TESTS=false
        RUN_MCP_TESTS=false
        RUN_INTEGRATION_TESTS=true
        ;;
    "all")
        RUN_UNIT_TESTS=true
        RUN_API_TESTS=true
        RUN_MCP_TESTS=true
        RUN_INTEGRATION_TESTS=true
        ;;
    "help"|"-h"|"--help")
        print_help
        exit 0
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        print_help
        exit 1
        ;;
esac

# Function to run unit tests
run_unit_tests() {
    print_header "Running Unit Tests..."
    
    # Add some test .env variables
    export OPENAI_API_KEY=fake-openai-key
    export WEAVIATE_API_KEY=fake-weaviate-key
    export WEAVIATE_URL=fake-weaviate-url.com

    # Run unit tests with the correct PYTHONPATH and robustly suppress Pydantic deprecation warnings
    # Exclude API and MCP specific tests
    PYTHONWARNINGS="ignore:PydanticDeprecatedSince20" PYTHONPATH=src uv run pytest -v \
        tests/test_common.py \
        tests/test_ragme.py \
        tests/test_ragme_agent.py \
        tests/test_local_agent.py \
        tests/test_vector_db.py \
        tests/test_vector_db_base.py \
        tests/test_vector_db_factory.py \
        tests/test_vector_db_milvus.py \
        tests/test_vector_db_weaviate.py \
        tests/test_add_json.py \
        tests/test_document_overlap.py \
        -k "not api and not mcp"
    
    print_header "Unit Tests Completed Successfully! 🎉"
}

# Function to run API tests
run_api_tests() {
    print_header "Running API Tests..."
    
    # Add some test .env variables
    export OPENAI_API_KEY=fake-openai-key
    export WEAVIATE_API_KEY=fake-weaviate-key
    export WEAVIATE_URL=fake-weaviate-url.com

    # Run API-specific tests
    PYTHONWARNINGS="ignore:PydanticDeprecatedSince20" PYTHONPATH=src uv run pytest -v \
        tests/test_api.py \
        -k "api"
    
    print_header "API Tests Completed Successfully! 🎉"
}

# Function to run MCP tests
run_mcp_tests() {
    print_header "Running MCP Server Tests..."
    
    # Add some test .env variables
    export OPENAI_API_KEY=fake-openai-key
    export WEAVIATE_API_KEY=fake-weaviate-key
    export WEAVIATE_URL=fake-weaviate-url.com

    # Run MCP-specific tests
    PYTHONWARNINGS="ignore:PydanticDeprecatedSince20" PYTHONPATH=src uv run pytest -v \
        tests/ \
        -k "mcp"
    
    print_header "MCP Server Tests Completed Successfully! 🎉"
}

# Function to run integration tests
run_integration_tests() {
    print_header "Running Integration Tests..."
    
    if [ -f "./test-integration.sh" ]; then
        print_status "Running integration test suite..."
        if ./test-integration.sh; then
            print_status "✓ Integration tests passed"
        else
            print_error "Integration tests failed"
            exit 1
        fi
    else
        print_warning "test-integration.sh not found, skipping integration tests"
    fi
    
    print_header "Integration Tests Completed Successfully! 🎉"
}

# Run unit tests if requested
if [ "$RUN_UNIT_TESTS" = true ]; then
    run_unit_tests
fi

# Run API tests if requested
if [ "$RUN_API_TESTS" = true ]; then
    run_api_tests
fi

# Run MCP tests if requested
if [ "$RUN_MCP_TESTS" = true ]; then
    run_mcp_tests
fi

# Run integration tests if requested
if [ "$RUN_INTEGRATION_TESTS" = true ]; then
    run_integration_tests
fi

print_status "All requested tests completed!" 