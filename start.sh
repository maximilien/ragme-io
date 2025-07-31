#!/bin/bash

# Load environment variables from .env file
set -a
[ -f .env ] && . .env
set +a

# RAGme Process Management Script
# Usage: ./start.sh [default|restart-frontend]

# Function to check if a port is in use and kill the process
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Port $port is already in use. Killing existing process..."
        lsof -ti :$port | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# Function to cleanup on error
cleanup() {
    echo "❌ Error occurred. Cleaning up..."
    if [ -f .pid ]; then
        while read pid; do
            if [ ! -z "$pid" ]; then
                kill $pid 2>/dev/null
            fi
        done < .pid
        rm -f .pid
    fi
    exit 1
}

# Function to stop existing processes
stop_existing() {
    echo "Stopping any existing RAGme processes..."
    
    # Stop processes from PID file
    if [ -f .pid ]; then
        echo "Stopping processes from PID file..."
        while read pid; do
            if [ ! -z "$pid" ]; then
                echo "Stopping process $pid..."
                kill $pid 2>/dev/null
                # Wait a bit and force kill if still running
                sleep 1
                if kill -0 $pid 2>/dev/null; then
                    echo "Force killing process $pid..."
                    kill -9 $pid 2>/dev/null
                fi
            fi
        done < .pid
        rm -f .pid
        sleep 2
    fi
    
    # Also kill any processes using our ports
    check_port 3020  # New Frontend
    check_port 8021  # API
    check_port 8022  # MCP
}

# Function to start core services (API, MCP, Agent)
start_core_services() {
    echo "Starting core RAGme services..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start api.py
    echo "Starting api.py..."
    uv run uvicorn src.ragme.api:app --reload --host 0.0.0.0 --port 8021 > logs/api.log 2>&1 &
    echo $! >> .pid
    sleep 3

    # Start mcp.py
    echo "Starting mcp.py..."
    uv run uvicorn src.ragme.mcp:app --reload --host 0.0.0.0 --port 8022 > logs/mcp.log 2>&1 &
    echo $! >> .pid
    sleep 3

    # Start local_agent.py
    echo "Starting local_agent.py..."
    uv run python -m src.ragme.local_agent > logs/agent.log 2>&1 &
    echo $! >> .pid
    sleep 3
}

# Function to start new frontend
start_new_frontend() {
    echo "Starting new frontend..."
    cd frontend
    npm install
    npm run build
    RAGME_API_URL=http://localhost:8021 npm start > ../logs/frontend.log 2>&1 &
    echo $! >> ../.pid
    cd ..
}

# Function to start default services (core + new frontend)
start_default() {
    echo "🚀 Starting RAGme with new frontend..."
    
    # Stop any existing processes
    stop_existing
    
    # Start core services
    start_core_services
    
    # Start new frontend
    start_new_frontend
    
    echo "✅ All services started successfully!"
}

# Function to restart frontend only
restart_frontend() {
    echo "🔄 Restarting frontend only..."
    
    # Kill existing frontend process
    check_port 3020
    
    # Remove frontend PID from .pid file if it exists
    if [ -f .pid ]; then
        # Create a temporary file without frontend PIDs
        grep -v "frontend" .pid > .pid.tmp 2>/dev/null || true
        mv .pid.tmp .pid
    fi
    
    # Start new frontend
    start_new_frontend
    
    echo "✅ Frontend restarted successfully!"
    echo "   • New Frontend: http://localhost:3020"
}

# Main script logic
case "${1:-default}" in
    "default"|"")
        start_default
        ;;
    "restart-frontend")
        restart_frontend
        ;;
    *)
        echo "Usage: $0 [default|restart-frontend]"
        echo ""
        echo "Commands:"
        echo "  default           - Start core services + new frontend (default)"
        echo "  restart-frontend  - Restart only the new frontend"
        echo ""
        echo "Examples:"
        echo "  ./start.sh              # Start with new frontend (default)"
        echo "  ./start.sh default      # Start with new frontend"
        echo "  ./start.sh restart-frontend # Restart frontend only"
        exit 1
        ;;
esac

# Show success message for default command
if [ "$1" = "default" ] || [ -z "$1" ]; then
    echo ""
    echo "✅ All RAGme processes started successfully!"
    echo ""
    echo "Process Management Commands:"
    echo "  ./stop.sh              # Stop all processes"
    echo "  ./stop.sh restart      # Restart all processes"
    echo "  ./stop.sh status       # Show process status"
    echo "  ./start.sh restart-frontend # Restart frontend only"
    echo ""
    echo "Access your RAGme services:"
    echo "  • New Frontend: http://localhost:3020"
    echo "  • API: http://localhost:8021"
    echo "  • MCP: http://localhost:8022"
fi 