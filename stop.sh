#!/bin/bash

# Load environment variables from .env file
set -a
[ -f .env ] && . .env
set +a

# RAGme Process Management Script
# Usage: ./stop.sh [stop|restart|status]

# Function to check if a port is in use and kill the process
kill_port_process() {
    local port=$1
    local service_name=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Killing $service_name process on port $port..."
        lsof -ti :$port | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# Function to stop all RAGme processes
stop_processes() {
    echo "Stopping all RAGme processes..."

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
    else
        echo "No .pid file found."
    fi

    # Also kill any processes using our specific ports
    kill_port_process 8020 "New Frontend"
    kill_port_process 8021 "FastAPI"
    kill_port_process 8022 "MCP"
    kill_port_process 9000 "MinIO"
    kill_port_process 9001 "MinIO Console"

    # Check if any processes are still running
    echo "Checking for any remaining processes..."
    if lsof -Pi :8020 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :8021 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :8022 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :9001 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Warning: Some processes may still be running on ports 8020, 8021, 8022, 9000, or 9001"
        return 1
    else
        echo "All RAGme processes stopped successfully."
        return 0
    fi
}

# Function to stop specific service
stop_service() {
    local service=$1
    echo "Stopping $service service..."
    
    case $service in
        "frontend")
            kill_port_process 8020 "New Frontend"
            # Remove frontend PID from .pid file if it exists
            if [ -f .pid ]; then
                # Create a temporary file without frontend PIDs
                grep -v "frontend" .pid > .pid.tmp 2>/dev/null || true
                mv .pid.tmp .pid
            fi
            ;;
        "api")
            kill_port_process 8021 "FastAPI"
            ;;
        "mcp")
            kill_port_process 8022 "MCP"
            ;;
        "minio")
            kill_port_process 9000 "MinIO"
            kill_port_process 9001 "MinIO Console"
            ;;
        *)
            echo "Unknown service: $service"
            echo "Available services: frontend, api, mcp, minio"
            return 1
            ;;
    esac
    
    echo "$service service stopped successfully."
}

# Function to identify service from PID
# This function analyzes the command line of a process to determine which RAGme service it is
identify_service() {
    local pid=$1
    
    # Check if process is still running
    if ! kill -0 $pid 2>/dev/null; then
        echo "stale"
        return
    fi
    
    # Get the command line for the PID
    local cmd=$(ps -p $pid -o command= 2>/dev/null)
    
    # Handle empty or null command
    if [[ -z "$cmd" ]]; then
        echo "Unknown"
        return
    fi
    
    # Identify services based on command patterns
    # API service patterns
    if [[ $cmd == *"src.ragme.apis.api"* ]] || [[ $cmd == *"uvicorn"* ]] && [[ $cmd == *"ragme.apis.api"* ]]; then
        echo "API"
    # MCP service patterns
    elif [[ $cmd == *"src.ragme.apis.mcp"* ]] || [[ $cmd == *"uvicorn"* ]] && [[ $cmd == *"ragme.apis.mcp"* ]]; then
        echo "MCP"
    # Agent service patterns
    elif [[ $cmd == *"src.ragme.agents.local_agent"* ]] || [[ $cmd == *"python -m src.ragme.agents.local_agent"* ]]; then
        echo "Agent"
    # Frontend service patterns
    elif [[ $cmd == *"npm start"* ]]; then
        echo "Frontend"
    # MinIO service patterns
    elif [[ $cmd == *"minio server"* ]]; then
        echo "MinIO"
    # Fallback patterns for uvicorn processes that might not match exact patterns
    elif [[ $cmd == *"uvicorn"* ]] && [[ $cmd == *"ragme"* ]]; then
        if [[ $cmd == *"api"* ]]; then
            echo "API"
        elif [[ $cmd == *"mcp"* ]]; then
            echo "MCP"
        else
            echo "Unknown RAGme Service"
        fi
    else
        echo "Unknown"
    fi
}

# Function to clean up stale PIDs from PID file
cleanup_stale_pids() {
    if [ -f .pid ]; then
        local temp_pid_file=".pid.tmp"
        local cleaned=false
        
        while read pid; do
            if [ ! -z "$pid" ]; then
                if kill -0 $pid 2>/dev/null; then
                    # PID is still running, keep it
                    echo $pid >> $temp_pid_file
                else
                    # PID is stale, remove it
                    echo "🧹 Cleaning up stale PID: $pid"
                    cleaned=true
                fi
            fi
        done < .pid
        
        if [ "$cleaned" = true ]; then
            mv $temp_pid_file .pid
            echo "✅ PID file cleaned up"
        else
            rm -f $temp_pid_file
        fi
    fi
}

# Function to show status of RAGme processes
show_status() {
    echo "=== RAGme Process Status ==="
    echo ""
    
    # Clean up stale PIDs first
    cleanup_stale_pids
    
    # Check PID file
    if [ -f .pid ]; then
        echo "📄 PID File Status:"
        echo "   PID file exists with the following processes:"
        while read pid; do
            if [ ! -z "$pid" ]; then
                local service=$(identify_service $pid)
                if [ "$service" = "stale" ]; then
                    echo "   ❌ Process $pid is not running (stale PID)"
                else
                    echo "   ✅ Process $pid is running ($service)"
                fi
            fi
        done < .pid
    else
        echo "📄 PID File Status: No .pid file found"
    fi
    
    echo ""
    echo "🌐 Port Status:"
    
    # Check each port
    local ports=("8020:New Frontend" "8021:FastAPI" "8022:MCP" "9000:MinIO" "9001:MinIO Console")
    local all_running=true
    
    for port_info in "${ports[@]}"; do
        IFS=':' read -r port service <<< "$port_info"
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            local pid=$(lsof -ti :$port)
            echo "   ✅ $service (port $port) - Running (PID: $pid)"
        else
            echo "   ❌ $service (port $port) - Not running"
            all_running=false
        fi
    done
    
    echo ""
    if [ "$all_running" = true ]; then
        echo "🎉 All RAGme services are running!"
        echo "   • New Frontend: http://localhost:8020"
        echo "   • API: http://localhost:8021"
        echo "   • MCP: http://localhost:8022"
        echo "   • MinIO: http://localhost:9000"
        echo "   • MinIO Console: http://localhost:9001"
    else
        echo "⚠️  Some RAGme services are not running."
        echo "   Use './stop.sh restart' to restart all services."
    fi
}

# Function to restart all RAGme processes
restart_processes() {
    echo "🔄 Restarting RAGme processes..."
    
    # Stop existing processes
    if stop_processes; then
        echo "✅ All processes stopped successfully"
    else
        echo "⚠️  Some processes may still be running, continuing with restart..."
    fi
    
    # Wait a moment for cleanup
    sleep 2
    
    # Start processes using start.sh (default - core services + new frontend only)
    echo "🚀 Starting RAGme processes (core services + new frontend)..."
    if [ -f start.sh ]; then
        ./start.sh default
    else
        echo "❌ Error: start.sh not found!"
        exit 1
    fi
}

# Main script logic
case "${1:-stop}" in
    "stop")
        stop_processes
        ;;
    "restart")
        restart_processes
        ;;
    "status")
        show_status
        ;;
    "frontend"|"api"|"mcp"|"minio")
        stop_service "$1"
        ;;
    *)
        echo "Usage: $0 [stop|restart|status|frontend|api|mcp|minio]"
        echo ""
        echo "Commands:"
        echo "  stop       - Stop all RAGme processes (default)"
        echo "  restart    - Stop and restart all RAGme processes"
        echo "  status     - Show status of all RAGme processes"
        echo ""
        echo "Examples:"
        echo "  ./stop.sh          # Stop all processes"
        echo "  ./stop.sh stop     # Stop all processes"
        echo "  ./stop.sh restart  # Restart all processes"
        echo "  ./stop.sh status   # Show process status"
        exit 1
        ;;
esac 