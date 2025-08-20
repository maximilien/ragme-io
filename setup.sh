#!/bin/bash

# RAGme.io Setup Script
# This script sets up all dependencies for the RAGme.io project

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
    echo -e "${BLUE}[SETUP]${NC} $1"
}

print_help() {
    echo -e "${BLUE}RAGme.io Setup Script${NC}"
    echo ""
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h        Show this help message"
    echo "  --skip-python     Skip Python dependency installation"
    echo "  --skip-node       Skip Node.js dependency installation"
    echo "  --skip-brew       Skip Homebrew dependency installation"
    echo "  --force           Force reinstall all dependencies"
    echo ""
    echo "This script will:"
    echo "  1. Check and install system dependencies (Homebrew, Node.js, Python)"
    echo "  2. Install Python dependencies using uv"
    echo "  3. Install Node.js dependencies for the frontend"
    echo "  4. Run initial tests to verify setup"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh                    # Full setup"
    echo "  ./setup.sh --skip-python      # Skip Python setup"
    echo "  ./setup.sh --force            # Force reinstall everything"
}

# Parse command line arguments
SKIP_PYTHON=false
SKIP_NODE=false
SKIP_BREW=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            print_help
            exit 0
            ;;
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --skip-node)
            SKIP_NODE=true
            shift
            ;;
        --skip-brew)
            SKIP_BREW=false
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

print_header "Starting RAGme.io Setup..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_warning "This script is optimized for macOS. Some features may not work on other systems."
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Homebrew if not present
install_homebrew() {
    if ! command_exists brew; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        print_status "Homebrew is already installed"
    fi
}

# Function to install Node.js if not present
install_nodejs() {
    if ! command_exists node; then
        print_status "Installing Node.js..."
        brew install node
    else
        print_status "Node.js is already installed ($(node --version))"
    fi
    
    if ! command_exists npm; then
        print_error "npm not found after Node.js installation"
        exit 1
    fi
}

# Function to install Python dependencies
install_python_deps() {
    print_header "Setting up Python dependencies..."
    
    # Check if uv is installed
    if ! command_exists uv; then
        print_status "Installing uv (Python package manager)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.cargo/env
    else
        print_status "uv is already installed ($(uv --version))"
    fi
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    uv sync
    
    # Install test dependencies
    print_status "Installing test dependencies..."
    uv pip install -r requirements-test.txt
    
    # Install development tools
    print_status "Installing development tools..."
    uv pip install ruff
    
    print_status "Python dependencies installed successfully!"
}

# Function to install Node.js dependencies
install_node_deps() {
    print_header "Setting up Node.js dependencies..."
    
    cd frontend
    
    # Clean install if force flag is set
    if [ "$FORCE" = true ]; then
        print_status "Force reinstalling Node.js dependencies..."
        rm -rf node_modules package-lock.json
    fi
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Test build
    print_status "Testing TypeScript compilation..."
    npm run build
    
    # Test linting
    print_status "Testing ESLint..."
    npm run lint
    
    # Verify ES module configuration
    print_status "Verifying ES module configuration..."
    if grep -q '"type": "module"' package.json && grep -q '"module": "ES2020"' tsconfig.json; then
        print_status "✅ ES module configuration verified"
    else
        print_warning "⚠️  ES module configuration may need attention"
    fi
    
    cd ..
    
    print_status "Node.js dependencies installed successfully!"
}

# Function to run initial tests
run_initial_tests() {
    print_header "Running initial tests..."
    
    # Test Python setup
    print_status "Testing Python setup..."
    if uv run --active python -c "import sys; print(f'Python {sys.version}')"; then
        print_status "✅ Python setup verified"
    else
        print_error "❌ Python setup failed"
        exit 1
    fi
    
    # Test Node.js setup
    print_status "Testing Node.js setup..."
    if cd frontend && npm run build && cd ..; then
        print_status "✅ Node.js setup verified"
    else
        print_error "❌ Node.js setup failed"
        exit 1
    fi
    
    # Run basic linting
    print_status "Running basic linting checks..."
    if ./tools/lint.sh; then
        print_status "✅ Linting checks passed"
    else
        print_warning "⚠️  Some linting checks failed (this is normal for initial setup)"
    fi
}

# Function to create .env file if it doesn't exist
setup_env_file() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        if [ -f env.example ]; then
            cp env.example .env
            print_warning "Created .env file from template. Please edit it with your API keys."
        else
            print_warning "No env.example found. You may need to create a .env file manually."
        fi
    else
        print_status ".env file already exists"
    fi
}

# Function to check system requirements
check_system_requirements() {
    print_header "Checking system requirements..."
    
    # Check available disk space (at least 1GB)
    available_space=$(df . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1048576 ]; then
        print_error "Insufficient disk space. Need at least 1GB available."
        exit 1
    fi
    
    # Check available memory (at least 2GB)
    total_mem=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    if [ "$total_mem" -lt 2147483648 ]; then
        print_warning "Low memory detected. Some operations may be slow."
    fi
    
    print_status "System requirements check passed"
}

# Main setup process
main() {
    print_header "RAGme.io Setup Process"
    echo "================================"
    
    # Check system requirements
    check_system_requirements
    
    # Install system dependencies
    if [ "$SKIP_BREW" = false ]; then
        print_header "Installing system dependencies..."
        install_homebrew
        install_nodejs
    else
        print_status "Skipping system dependency installation"
    fi
    
    # Setup environment file
    setup_env_file
    
    # Install Python dependencies
    if [ "$SKIP_PYTHON" = false ]; then
        install_python_deps
    else
        print_status "Skipping Python dependency installation"
    fi
    
    # Install Node.js dependencies
    if [ "$SKIP_NODE" = false ]; then
        install_node_deps
    else
        print_status "Skipping Node.js dependency installation"
    fi
    
    # Run initial tests
    run_initial_tests
    
    print_header "Setup Complete! 🎉"
    echo "================================"
    print_status "RAGme.io is now ready to use!"
    echo ""
    print_status "Next steps:"
    echo "  1. Edit .env file with your API keys"
    echo "  2. Run './start.sh' to start the services"
    echo "  3. Visit http://localhost:8020 to access the frontend"
    echo ""
    print_status "Useful commands:"
    echo "  ./start.sh              # Start all services"
    echo "  ./stop.sh               # Stop all services"
    echo "  ./test.sh unit          # Run unit tests"
    echo "  ./tools/lint.sh         # Run linting checks"
    echo ""
    print_status "For more information, see README.md"
}

# Run main function
main "$@"
