#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# Test runner with environment backup and restoration
# This script ensures that tests run in isolation without affecting the main environment

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
print_help() {
    echo "Usage: $0 <test_type>"
    echo ""
    echo "Test types:"
    echo "  integration      Run full integration tests"
    echo "  integration-fast Run fast integration tests"
    echo "  agents          Run agent integration tests"
    echo "  help            Show this help message"
    echo ""
    echo "This script will:"
    echo "  1. Stop all RAGme services"
    echo "  2. Backup your current environment (.env and config.yaml)"
    echo "  3. Modify configuration for test collections"
    echo "  4. Run the specified tests"
    echo "  5. Restore your original environment"
    echo "  6. Restart services"
    echo ""
    echo "Examples:"
    echo "  $0 integration-fast  # Run fast integration tests"
    echo "  $0 integration       # Run full integration tests"
    echo "  $0 agents           # Run agent tests"
}

# Generate timestamped backup names
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ENV_BACKUP=".env.backup_${TIMESTAMP}"
CONFIG_BACKUP="config.yaml.backup_${TIMESTAMP}"

# Function to stop all RAGme services
stop_services() {
    print_status "Stopping all RAGme services..."
    if [ -f "./stop.sh" ]; then
        ./stop.sh > /dev/null 2>&1 || true
        print_success "Services stopped"
    else
        print_warning "stop.sh not found, services may still be running"
    fi
    
    # Wait a moment for services to fully stop
    sleep 2
}

# Function to start RAGme services
start_services() {
    print_status "Starting RAGme services..."
    if [ -f "./start.sh" ]; then
        ./start.sh > /dev/null 2>&1 &
        print_success "Services started in background"
    else
        print_warning "start.sh not found, please start services manually"
    fi
}

# Function to backup current environment
backup_environment() {
    print_status "Backing up current environment..."
    
    # Backup .env file
    if [ -f ".env" ]; then
        cp .env "$ENV_BACKUP"
        print_success "Backed up .env to $ENV_BACKUP"
    else
        print_warning ".env file not found"
    fi
    
    # Backup config.yaml
    if [ -f "config.yaml" ]; then
        cp config.yaml "$CONFIG_BACKUP"
        print_success "Backed up config.yaml to $CONFIG_BACKUP"
    else
        print_warning "config.yaml not found"
    fi
    
    return 0
}

# Function to setup test environment
setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Create test configuration by copying existing config and modifying collection names
    if [ -f "config.yaml" ]; then
        # Copy existing config and modify only the collection names
        cp config.yaml config.yaml.test_temp
        # Replace environment variable references with test collection names using sed
        sed -i.bak 's/\${VECTOR_DB_TEXT_COLLECTION_NAME}/test_integration/g' config.yaml.test_temp
        sed -i.bak 's/\${VECTOR_DB_IMAGE_COLLECTION_NAME}/test_integration_images/g' config.yaml.test_temp
        # Remove backup files created by sed
        rm -f config.yaml.test_temp.bak
    else
        # Create new config if it doesn't exist
        cat > config.yaml.test_temp << 'EOF'
# Test configuration for integration tests
# This ensures tests use separate collections

vector_db:
  type: "weaviate"
  weaviate:
    url: "${WEAVIATE_URL}"
    api_key: "${WEAVIATE_API_KEY}"
    collections:
      - name: "test_integration"
      - name: "test_integration_images"

# Test-specific settings
features:
  bypass_delete_confirmation: true
  enable_test_mode: true

# Use test collections
test_collections:
  text_collection: "test_integration"
  image_collection: "test_integration_images"
EOF
    fi

    # Replace config.yaml with test configuration
    cp config.yaml.test_temp config.yaml
    print_success "Test configuration applied (preserved existing settings)"
    
    # Create test .env file by copying existing .env and modifying collection names
    if [ -f ".env" ]; then
        # Copy existing .env and modify only the collection names
        cp .env .env.test_temp
        
        # Check if the variables exist and replace them, or add them if they don't exist
        if grep -q "VECTOR_DB_TEXT_COLLECTION_NAME=" .env.test_temp; then
            # Variable exists, replace it
            sed -i.bak 's/VECTOR_DB_TEXT_COLLECTION_NAME=.*/VECTOR_DB_TEXT_COLLECTION_NAME=test_integration/' .env.test_temp
        else
            # Variable doesn't exist, add it
            echo "VECTOR_DB_TEXT_COLLECTION_NAME=test_integration" >> .env.test_temp
        fi
        
        if grep -q "VECTOR_DB_IMAGE_COLLECTION_NAME=" .env.test_temp; then
            # Variable exists, replace it
            sed -i.bak 's/VECTOR_DB_IMAGE_COLLECTION_NAME=.*/VECTOR_DB_IMAGE_COLLECTION_NAME=test_integration_images/' .env.test_temp
        else
            # Variable doesn't exist, add it
            echo "VECTOR_DB_IMAGE_COLLECTION_NAME=test_integration_images" >> .env.test_temp
        fi
        
        # Remove backup files created by sed
        rm -f .env.test_temp.bak
    else
        # Create new .env if it doesn't exist
        cat > .env.test_temp << 'EOF'
# Test environment variables
VECTOR_DB_TYPE=weaviate
VECTOR_DB_TEXT_COLLECTION_NAME=test_integration
VECTOR_DB_IMAGE_COLLECTION_NAME=test_integration_images
WEAVIATE_URL=${WEAVIATE_URL}
WEAVIATE_API_KEY=${WEAVIATE_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
EOF
    fi

    # Replace .env with test environment
    cp .env.test_temp .env
    print_success "Test environment applied (preserved existing variables)"
    
    return 0
}

# Function to restore environment
restore_environment() {
    print_status "Restoring original environment..."
    
    # Restore .env file
    if [ -f "$ENV_BACKUP" ]; then
        cp "$ENV_BACKUP" .env
        print_success "Restored .env from $ENV_BACKUP"
    else
        print_warning "No .env backup found"
    fi
    
    # Restore config.yaml
    if [ -f "$CONFIG_BACKUP" ]; then
        cp "$CONFIG_BACKUP" config.yaml
        print_success "Restored config.yaml from $CONFIG_BACKUP"
    else
        print_warning "No config.yaml backup found"
    fi
    
    # Clean up backup files
    cleanup_backup_files
    
    return 0
}

# Function to cleanup backup files
cleanup_backup_files() {
    print_status "Cleaning up backup files..."
    
    # Clean up our script's backup files
    if [ -f "$ENV_BACKUP" ]; then
        rm "$ENV_BACKUP"
        print_status "🗑️ Removed $ENV_BACKUP"
    fi
    
    if [ -f "$CONFIG_BACKUP" ]; then
        rm "$CONFIG_BACKUP"
        print_status "🗑️ Removed $CONFIG_BACKUP"
    fi
    
    # Clean up test temp files
    if [ -f "config.yaml.test_temp" ]; then
        rm "config.yaml.test_temp"
        print_status "🗑️ Removed config.yaml.test_temp"
    fi
    
    if [ -f ".env.test_temp" ]; then
        rm ".env.test_temp"
        print_status "🗑️ Removed .env.test_temp"
    fi
    
    # Clean up any integration backup files that might have been left behind
    if [ -f ".env.integration_backup" ]; then
        rm ".env.integration_backup"
        print_status "🗑️ Removed .env.integration_backup"
    fi
    
    if [ -f "config.yaml.test_backup" ]; then
        rm "config.yaml.test_backup"
        print_status "🗑️ Removed config.yaml.test_backup"
    fi
    
    if [ -f "config.yaml.test_temp" ]; then
        rm "config.yaml.test_temp"
        print_status "🗑️ Removed config.yaml.test_temp"
    fi
}

# Function to run tests
run_tests() {
    local test_type=$1
    
    print_header "Running $test_type tests..."
    
    case "$test_type" in
        "integration")
            print_status "Running full integration tests..."
            ./test.sh integration
            ;;
        "integration-fast")
            print_status "Running fast integration tests..."
            ./test.sh integration-fast
            ;;
        "agents")
            print_status "Running agent integration tests..."
            ./test.sh agents
            ;;
        *)
            print_error "Unknown test type: $test_type"
            return 1
            ;;
    esac
}

# Function to handle cleanup on exit
cleanup_on_exit() {
    print_warning "🛑 Interrupted! Restoring environment..."
    restore_environment
    start_services
    exit 1
}

# Main execution
main() {
    local test_type=$1
    
    # Check if test type is provided
    if [ -z "$test_type" ]; then
        print_error "No test type specified"
        print_help
        exit 1
    fi
    
    # Validate test type
    case "$test_type" in
        "integration"|"integration-fast"|"agents")
            ;;
        "help"|"-h"|"--help")
            print_help
            exit 0
            ;;
        *)
            print_error "Unknown test type: $test_type"
            print_help
            exit 1
            ;;
    esac
    
    # Set up signal handlers for cleanup
    trap cleanup_on_exit INT TERM
    
    print_header "Starting test run with environment backup for: $test_type"
    echo "================================================================"
    
    # Step 1: Stop all services
    if ! stop_services; then
        print_error "❌ Failed to stop services"
        exit 1
    fi
    
    # Step 2: Backup current environment
    if ! backup_environment; then
        print_error "❌ Failed to backup environment"
        exit 1
    fi
    
    # Step 3: Setup test environment
    if ! setup_test_environment; then
        print_error "❌ Failed to setup test environment"
        restore_environment
        start_services
        exit 1
    fi
    
    # Step 4: Run tests
    print_header "Running tests..."
    test_exit_code=0
    if run_tests "$test_type"; then
        print_status "✅ Tests completed successfully"
    else
        print_error "❌ Tests failed"
        test_exit_code=1
        # Don't exit here - we still want to restore the environment
    fi
    
    # Step 5: Restore environment (regardless of test outcome)
    restore_exit_code=0
    if restore_environment; then
        print_status "✅ Environment restoration completed successfully"
    else
        print_warning "⚠️ Environment restoration had issues"
        restore_exit_code=1
    fi
    
    # Step 6: Start services
    if ! start_services; then
        print_warning "⚠️ Failed to start services"
        restore_exit_code=1
    fi
    
    # Final status
    if [ $test_exit_code -eq 0 ] && [ $restore_exit_code -eq 0 ]; then
        print_header "🎉 Test run completed successfully!"
        print_status "Environment has been restored to original state"
        print_status "Services have been restarted"
        exit 0
    elif [ $test_exit_code -eq 0 ]; then
        print_header "⚠️ Tests passed but environment restoration had issues"
        print_warning "Please check your configuration files manually"
        exit 1
    else
        print_error "❌ Tests failed"
        print_warning "Environment restoration attempted but may have issues"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
