#!/bin/bash

# RAGme Process Management Script
# Usage: ./stop.sh [stop|restart|status|legacy-ui]

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
    kill_port_process 3020 "New Frontend"
    kill_port_process 8020 "Legacy Streamlit UI"
    kill_port_process 8021 "FastAPI"
    kill_port_process 8022 "MCP"

    # Check if any processes are still running
    echo "Checking for any remaining processes..."
    if lsof -Pi :3020 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :8020 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :8021 -sTCP:LISTEN -t >/dev/null 2>&1 || \
       lsof -Pi :8022 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Warning: Some processes may still be running on ports 3020, 8020, 8021, or 8022"
        return 1
    else
        echo "All RAGme processes stopped successfully."
        return 0
    fi
}

# Function to stop legacy UI only
stop_legacy_ui() {
    echo "Stopping legacy UI only..."
    
    # Kill legacy UI process on port 8020
    kill_port_process 8020 "Legacy Streamlit UI"
    
    # Remove legacy UI PID from .pid file if it exists
    if [ -f .pid ]; then
        # Create a temporary file without legacy UI PIDs
        grep -v "streamlit" .pid > .pid.tmp 2>/dev/null || true
        mv .pid.tmp .pid
    fi
    
    echo "✅ Legacy UI stopped successfully!"
}

# Function to show status of RAGme processes
show_status() {
    echo "=== RAGme Process Status ==="
    echo ""
    
    # Check PID file
    if [ -f .pid ]; then
        echo "📄 PID File Status:"
        echo "   PID file exists with the following processes:"
        while read pid; do
            if [ ! -z "$pid" ]; then
                if kill -0 $pid 2>/dev/null; then
                    echo "   ✅ Process $pid is running"
                else
                    echo "   ❌ Process $pid is not running (stale PID)"
                fi
            fi
        done < .pid
    else
        echo "📄 PID File Status: No .pid file found"
    fi
    
    echo ""
    echo "🌐 Port Status:"
    
    # Check each port
    local ports=("3020:New Frontend" "8020:Legacy Streamlit UI" "8021:FastAPI" "8022:MCP")
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
        echo "   • New Frontend: http://localhost:3020"
        echo "   • Legacy UI: http://localhost:8020"
        echo "   • API: http://localhost:8021"
        echo "   • MCP: http://localhost:8022"
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
    "legacy-ui")
        stop_legacy_ui
        ;;
    *)
        echo "Usage: $0 [stop|restart|status|legacy-ui]"
        echo ""
        echo "Commands:"
        echo "  stop       - Stop all RAGme processes (default)"
        echo "  restart    - Stop and restart all RAGme processes"
        echo "  status     - Show status of all RAGme processes"
        echo "  legacy-ui  - Stop legacy UI only"
        echo ""
        echo "Examples:"
        echo "  ./stop.sh          # Stop all processes"
        echo "  ./stop.sh stop     # Stop all processes"
        echo "  ./stop.sh restart  # Restart all processes"
        echo "  ./stop.sh status   # Show process status"
        echo "  ./stop.sh legacy-ui # Stop legacy UI only"
        exit 1
        ;;
esac 