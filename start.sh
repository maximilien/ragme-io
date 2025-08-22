#!/bin/bash

# Load environment variables from .env file
set -a
[ -f .env ] && . .env
set +a

# RAGme Process Management Script
# Usage: ./start.sh [default|compile-frontend|restart-frontend|restart-backend]

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
    check_port ${RAGME_FRONTEND_PORT:-8020}  # New Frontend
    check_port ${RAGME_API_PORT:-8021}  # API
    check_port ${RAGME_MCP_PORT:-8022}  # MCP
}

# Function to start MinIO service
start_minio() {
    echo "Starting MinIO service..."
    
    # Check if MinIO is already running
    if lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "MinIO is already running on port 9000"
        return 0
    fi
    
    # Create minio_data directory if it doesn't exist
    mkdir -p minio_data
    
    # Start MinIO server
    echo "Starting MinIO server on port 9000..."
    minio server minio_data --console-address ":9001" > logs/minio.log 2>&1 &
    echo $! >> .pid
    sleep 3
    
    echo "✅ MinIO service started successfully!"
    echo "MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
}

# Function to start core services (API, MCP, Agent)
start_core_services() {
    echo "Starting core RAGme services..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start MinIO first
    start_minio
    
    # Start api.py
    echo "Starting api.py..."
    uv run uvicorn src.ragme.apis.api:app --reload --host 0.0.0.0 --port ${RAGME_API_PORT:-8021} > logs/api.log 2>&1 &
    echo $! >> .pid
    sleep 3

    # Start mcp.py
    echo "Starting mcp.py..."
    uv run uvicorn src.ragme.apis.mcp:app --reload --host 0.0.0.0 --port ${RAGME_MCP_PORT:-8022} > logs/mcp.log 2>&1 &
    echo $! >> .pid
    sleep 3

    # Start local_agent.py
    echo "Starting local_agent.py..."
    uv run python -m src.ragme.agents.local_agent > logs/agent.log 2>&1 &
    echo $! >> .pid
    sleep 3
}

# Function to start new frontend
start_new_frontend() {
    echo "Starting new frontend..."
    cd frontend
    npm install
    npm run build
    RAGME_API_URL=http://localhost:${RAGME_API_PORT:-8021} npm start > ../logs/frontend.log 2>&1 &
    echo $! >> ../.pid
    cd ..
}

# Function to start specific service
start_service() {
    local service=$1
    echo "Starting $service service..."
    
    case $service in
        "frontend")
            check_port ${RAGME_FRONTEND_PORT:-8020}
            start_new_frontend
            ;;
        "api")
            check_port ${RAGME_API_PORT:-8021}
            echo "Starting api.py..."
            uv run uvicorn src.ragme.apis.api:app --reload --host 0.0.0.0 --port ${RAGME_API_PORT:-8021} > logs/api.log 2>&1 &
            echo $! >> .pid
            sleep 3
            ;;
        "mcp")
            check_port ${RAGME_MCP_PORT:-8022}
            echo "Starting mcp.py..."
            uv run uvicorn src.ragme.apis.mcp:app --reload --host 0.0.0.0 --port ${RAGME_MCP_PORT:-8022} > logs/mcp.log 2>&1 &
            echo $! >> .pid
            sleep 3
            ;;
        "minio")
            start_minio
            ;;
        *)
            echo "Unknown service: $service"
            echo "Available services: frontend, api, mcp, minio"
            return 1
            ;;
    esac
    
    echo "$service service started successfully."
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

# Function to compile frontend only (no restart)
compile_frontend() {
    echo "🔨 Compiling frontend..."
    
    cd frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing npm dependencies..."
        npm install
    else
        echo "📦 Ensuring npm dependencies are up to date..."
        npm install
    fi
    
    # Build/compile the frontend
    echo "🏗️ Building TypeScript..."
    npm run build
    
    cd ..
    
    echo "✅ Frontend compiled successfully!"
    echo "   • TypeScript compiled to JavaScript"
    echo "   • Ready for deployment"
    echo ""
    echo "💡 To restart the frontend server with new changes:"
    echo "   ./start.sh restart-frontend"
}

# Function to restart frontend only
restart_frontend() {
    echo "🔄 Restarting frontend only..."
    
    # Kill existing frontend process
    check_port 8020
    
    # Remove frontend PID from .pid file if it exists
    if [ -f .pid ]; then
        # Create a temporary file without frontend PIDs
        grep -v "frontend" .pid > .pid.tmp 2>/dev/null || true
        mv .pid.tmp .pid
    fi
    
    # Start new frontend
    start_new_frontend
    
    echo "✅ Frontend restarted successfully!"
    echo "   • New Frontend: http://localhost:8020"
}

# Function to restart backend services only (API, MCP, Agent)
restart_backend() {
    echo "🔄 Restarting backend services only..."
    
    # Kill existing backend processes
    check_port 8021  # API
    check_port 8022  # MCP
    
    # Remove backend PIDs from .pid file if it exists
    if [ -f .pid ]; then
        # Create a temporary file keeping only frontend PIDs
        # This is a simple approach - we'll just keep the last PID (frontend)
        # and remove the first 3 PIDs (api, mcp, agent)
        if [ $(wc -l < .pid) -ge 3 ]; then
            tail -n +4 .pid > .pid.tmp 2>/dev/null || true
            mv .pid.tmp .pid
        else
            # If less than 3 PIDs, just clear the file
            rm -f .pid
        fi
    fi
    
    # Start core backend services
    start_core_services
    
    echo "✅ Backend services restarted successfully!"
    echo "   • API: http://localhost:8021"
    echo "   • MCP: http://localhost:8022"
    echo "   • Local Agent: Running in background"
}

# Main script logic
case "${1:-default}" in
    "default"|"")
        start_default
        ;;
    "compile-frontend")
        compile_frontend
        ;;
    "restart-frontend")
        restart_frontend
        ;;
    "restart-backend")
        restart_backend
        ;;
    "frontend"|"api"|"mcp")
        start_service "$1"
        ;;
    *)
        echo "Usage: $0 [default|compile-frontend|restart-frontend|restart-backend|frontend|api|mcp]"
        echo ""
        echo "Commands:"
        echo "  default           - Start core services + new frontend (default)"
        echo "  compile-frontend  - Compile/build frontend TypeScript only (no restart)"
        echo "  restart-frontend  - Restart only the new frontend"
        echo "  restart-backend   - Restart backend services (API, MCP, Agent)"
        echo ""
        echo "Examples:"
        echo "  ./start.sh              # Start with new frontend (default)"
        echo "  ./start.sh default      # Start with new frontend"
        echo "  ./start.sh compile-frontend  # Compile frontend after config/code changes"
        echo "  ./start.sh restart-frontend # Restart frontend only"
        echo "  ./start.sh restart-backend  # Restart backend services only"
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
    echo "  ./start.sh restart-backend  # Restart backend services only"
    echo ""
    echo "Access your RAGme services:"
    echo "  • New Frontend: http://localhost:8020"
    echo "  • API: http://localhost:8021"
    echo "  • MCP: http://localhost:8022"
fi 