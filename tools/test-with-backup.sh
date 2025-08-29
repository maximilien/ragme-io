#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# Test Wrapper with Environment Backup/Restore
# This script backs up the current .env and config.yaml, sets up test collections,
# runs the specified tests, and restores the original configuration regardless of outcome.

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
    echo -e "${BLUE}RAGme Test Wrapper with Environment Backup${NC}"
    echo ""
    echo "Usage: ./tools/test-with-backup.sh [TEST_TYPE]"
    echo ""
    echo "This script will:"
    echo "  1. Backup current .env and config.yaml"
    echo "  2. Set collections to test_integration and test_integration_images"
    echo "  3. Run the specified tests"
    echo "  4. Restore original configuration (regardless of test outcome)"
    echo ""
    echo "Test Types:"
    echo "  integration     Run full integration tests"
    echo "  integration-fast Run fast integration tests"
    echo "  agents          Run agent integration tests"
    echo ""
    echo "Examples:"
    echo "  ./tools/test-with-backup.sh integration     # Run full integration tests"
    echo "  ./tools/test-with-backup.sh integration-fast # Run fast integration tests"
    echo "  ./tools/test-with-backup.sh agents          # Run agent tests"
    echo ""
}

# Configuration
TEST_COLLECTION_NAME="test_integration"
TEST_IMAGE_COLLECTION_NAME="test_integration_images"
BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ENV_BACKUP=".env.backup_${BACKUP_TIMESTAMP}"
CONFIG_BACKUP="config.yaml.backup_${BACKUP_TIMESTAMP}"

# Function to backup current environment
backup_environment() {
    print_header "Backing up current environment..."
    
    # Backup .env file
    if [ -f ".env" ]; then
        cp .env "$ENV_BACKUP"
        print_status "✅ Backed up .env to $ENV_BACKUP"
    else
        print_warning "⚠️ .env file not found, will create one for tests"
    fi
    
    # Backup config.yaml
    if [ -f "config.yaml" ]; then
        cp config.yaml "$CONFIG_BACKUP"
        print_status "✅ Backed up config.yaml to $CONFIG_BACKUP"
    else
        print_error "❌ config.yaml not found!"
        return 1
    fi
    
    print_status "✅ Environment backup completed"
}

# Function to setup test environment
setup_test_environment() {
    print_header "Setting up test environment..."
    
    # Use the existing config manager to handle the setup
    if [ -f "tests/integration/config_manager.py" ]; then
        print_status "Using existing config manager for test setup..."
        
        # Run the setup using Python from virtual environment
        source .venv/bin/activate
        python -c "
import sys
sys.path.append('tests/integration')
from config_manager import setup_test_config
if setup_test_config():
    print('✅ Test configuration setup successful')
    exit(0)
else:
    print('❌ Test configuration setup failed')
    exit(1)
"
        
        if [ $? -eq 0 ]; then
            print_status "✅ Test environment setup completed"
            return 0
        else
            print_error "❌ Test environment setup failed"
            return 1
        fi
    else
        print_error "❌ config_manager.py not found in tests/integration/"
        return 1
    fi
}

# Function to restore original environment
restore_environment() {
    print_header "Restoring original environment..."
    
    # Use the existing config manager to handle the restoration
    if [ -f "tests/integration/config_manager.py" ]; then
        print_status "Using existing config manager for restoration..."
        
        # Run the teardown using Python with better error handling
        source .venv/bin/activate
        python -c "
import sys
sys.path.append('tests/integration')
try:
    from config_manager import teardown_test_config
    if teardown_test_config():
        print('✅ Test configuration teardown successful')
        exit(0)
    else:
        print('❌ Test configuration teardown failed')
        exit(1)
except Exception as e:
    print(f'❌ Error during teardown: {e}')
    exit(1)
"
        
        teardown_exit_code=$?
        if [ $teardown_exit_code -eq 0 ]; then
            print_status "✅ Environment restoration completed"
        else
            print_warning "⚠️ Environment restoration had issues, attempting manual fallback..."
            
            # Manual restoration as fallback
            if [ -f "$ENV_BACKUP" ]; then
                cp "$ENV_BACKUP" .env
                print_status "✅ Restored .env from backup"
            fi
            
            if [ -f "$CONFIG_BACKUP" ]; then
                cp "$CONFIG_BACKUP" config.yaml
                print_status "✅ Restored config.yaml from backup"
            fi
        fi
    else
        print_error "❌ config_manager.py not found, attempting manual restoration..."
        
        # Manual restoration as fallback
        if [ -f "$ENV_BACKUP" ]; then
            cp "$ENV_BACKUP" .env
            print_status "✅ Restored .env from backup"
        fi
        
        if [ -f "$CONFIG_BACKUP" ]; then
            cp "$CONFIG_BACKUP" config.yaml
            print_status "✅ Restored config.yaml from backup"
        fi
    fi
    
    # Clean up backup files
    cleanup_backup_files
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
    
    # Clean up any leftover backup files from previous runs (including timestamped ones)
    for backup_file in .env.backup_* config.yaml.backup_*; do
        if [ -f "$backup_file" ]; then
            rm "$backup_file"
            print_status "🗑️ Removed leftover backup: $backup_file"
        fi
    done
    
    # Also clean up any config manager backup files
    if [ -f "config.yaml.test_backup" ]; then
        rm "config.yaml.test_backup"
        print_status "🗑️ Removed config manager backup: config.yaml.test_backup"
    fi
    
    if [ -f ".env.integration_backup" ]; then
        rm ".env.integration_backup"
        print_status "🗑️ Removed config manager backup: .env.integration_backup"
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
    
    # Step 1: Backup current environment
    if ! backup_environment; then
        print_error "❌ Failed to backup environment"
        exit 1
    fi
    
    # Step 2: Setup test environment
    if ! setup_test_environment; then
        print_error "❌ Failed to setup test environment"
        restore_environment
        exit 1
    fi
    
    # Step 3: Run tests
    print_header "Running tests..."
    test_exit_code=0
    if run_tests "$test_type"; then
        print_status "✅ Tests completed successfully"
    else
        print_error "❌ Tests failed"
        test_exit_code=1
        # Don't exit here - we still want to restore the environment
    fi
    
    # Step 4: Restore environment (regardless of test outcome)
    restore_exit_code=0
    if restore_environment; then
        print_status "✅ Environment restoration completed successfully"
    else
        print_warning "⚠️ Environment restoration had issues"
        restore_exit_code=1
    fi
    
    # Final status
    if [ $test_exit_code -eq 0 ] && [ $restore_exit_code -eq 0 ]; then
        print_header "🎉 Test run completed successfully!"
        print_status "Environment has been restored to original state"
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
