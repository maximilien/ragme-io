#!/bin/bash

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
kill_port_process 8020 "Streamlit UI"
kill_port_process 8021 "FastAPI"
kill_port_process 8022 "MCP"

# Check if any processes are still running
echo "Checking for any remaining processes..."
if lsof -Pi :8020 -sTCP:LISTEN -t >/dev/null 2>&1 || \
   lsof -Pi :8021 -sTCP:LISTEN -t >/dev/null 2>&1 || \
   lsof -Pi :8022 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Warning: Some processes may still be running on ports 8020, 8021, or 8022"
else
    echo "All RAGme processes stopped successfully."
fi 