#!/bin/bash

# Local Weaviate Management Script (Podman Version)
# Usage: ./tools/weaviate-local.sh [start|stop|restart|status|logs]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if Podman is available
check_podman() {
    if ! command -v podman >/dev/null 2>&1; then
        echo -e "${RED}❌ Podman is not installed. Please install Podman first.${NC}"
        exit 1
    fi
    
    # Try to initialize podman if needed
    if ! podman version >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Podman needs initialization. Trying to fix permissions...${NC}"
        # Try to create config directory with proper permissions
        mkdir -p ~/.config 2>/dev/null || true
        chmod 755 ~/.config 2>/dev/null || true
        
        # Try to initialize podman
        podman machine init 2>/dev/null || true
        podman machine start 2>/dev/null || true
        
        if ! podman version >/dev/null 2>&1; then
            echo -e "${RED}❌ Podman is not running. Please start Podman manually.${NC}"
            echo -e "${YELLOW}   Try: podman machine start${NC}"
            exit 1
        fi
    fi
}

# Function to start local Weaviate
start_weaviate() {
    echo -e "${BLUE}🚀 Starting local Weaviate with Podman...${NC}"
    check_podman
    
    if podman ps --format "table {{.Names}}" | grep -q "weaviate"; then
        echo -e "${YELLOW}⚠️  Weaviate is already running${NC}"
        return
    fi
    
    # Use podman-compose if available, otherwise use podman directly
    if command -v podman-compose >/dev/null 2>&1; then
        podman-compose -f "$(dirname "$0")/podman-compose.weaviate.yml" up -d
    else
        # Fallback to direct podman commands
        echo -e "${YELLOW}⚠️  podman-compose not found, using direct podman commands${NC}"
        podman run -d \
            --name weaviate \
            -p 8080:8080 \
            -e QUERY_DEFAULTS_LIMIT=25 \
            -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
            -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
            -e DEFAULT_VECTORIZER_MODULE='text2vec-weaviate' \
            -e ENABLE_MODULES='text2vec-weaviate' \
            -e CLUSTER_HOSTNAME='node1' \
            -v weaviate_data:/var/lib/weaviate \
            semitechnologies/weaviate:1.31.5
    fi
    
    echo -e "${GREEN}✅ Local Weaviate started successfully!${NC}"
    echo -e "${BLUE}   • URL: http://localhost:8080${NC}"
    echo -e "${BLUE}   • Health check: http://localhost:8080/v1/.well-known/ready${NC}"
    echo -e "${YELLOW}   • Wait a moment for Weaviate to fully initialize...${NC}"
}

# Function to stop local Weaviate
stop_weaviate() {
    echo -e "${BLUE}🛑 Stopping local Weaviate...${NC}"
    check_podman
    
    if command -v podman-compose >/dev/null 2>&1; then
        podman-compose -f "$(dirname "$0")/podman-compose.weaviate.yml" down
    else
        # Fallback to direct podman commands
        podman stop weaviate 2>/dev/null || true
        podman rm weaviate 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Local Weaviate stopped successfully!${NC}"
}

# Function to restart local Weaviate
restart_weaviate() {
    echo -e "${BLUE}🔄 Restarting local Weaviate...${NC}"
    stop_weaviate
    sleep 2
    start_weaviate
}

# Function to show status
show_status() {
    echo -e "${BLUE}=== Local Weaviate Status ===${NC}"
    echo ""
    
    check_podman
    
    if podman ps --format "table {{.Names}}" | grep -q "weaviate"; then
        echo -e "${GREEN}✅ Weaviate is running${NC}"
        echo -e "${BLUE}   • URL: http://localhost:8080${NC}"
        echo -e "${BLUE}   • Health: http://localhost:8080/v1/.well-known/ready${NC}"
        
        # Check if Weaviate is ready
        if curl -s --max-time 10 http://localhost:8080/v1/.well-known/ready >/dev/null 2>&1; then
            echo -e "${GREEN}   • Status: Ready${NC}"
        else
            echo -e "${YELLOW}   • Status: Starting up...${NC}"
        fi
    else
        echo -e "${RED}❌ Weaviate is not running${NC}"
        echo -e "${YELLOW}   • Start with: ./tools/weaviate-local.sh start${NC}"
    fi
    echo ""
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}📋 Weaviate logs (press Ctrl+C to exit):${NC}"
    check_podman
    
    if command -v podman-compose >/dev/null 2>&1; then
        podman-compose -f "$(dirname "$0")/podman-compose.weaviate.yml" logs -f weaviate
    else
        # Try to find the actual container name
        container_name=$(podman ps --format "table {{.Names}}" | grep -E "(weaviate|ragme)" | head -1)
        if [ -n "$container_name" ]; then
            podman logs -f "$container_name"
        else
            echo -e "${RED}❌ No Weaviate container found${NC}"
        fi
    fi
}

# Function to show help
show_help() {
    echo -e "${BLUE}Local Weaviate Management Script (Podman Version)${NC}"
    echo ""
    echo "Usage: $0 [start|stop|restart|status|logs]"
    echo ""
    echo "Commands:"
    echo -e "  ${GREEN}start${NC}    - Start local Weaviate container"
    echo -e "  ${GREEN}stop${NC}     - Stop local Weaviate container"
    echo -e "  ${GREEN}restart${NC}  - Restart local Weaviate container"
    echo -e "  ${GREEN}status${NC}   - Show Weaviate status"
    echo -e "  ${GREEN}logs${NC}     - Show Weaviate logs"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start Weaviate"
    echo "  $0 status    # Check status"
    echo "  $0 logs      # View logs"
    echo ""
    echo "Note: This script manages a local Weaviate instance using Podman."
    echo "      If podman-compose is not available, it will use direct podman commands."
}

# Main script logic
case "${1:-help}" in
    "start")
        start_weaviate
        ;;
    "stop")
        stop_weaviate
        ;;
    "restart")
        restart_weaviate
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac 