#!/bin/bash

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Port $port is already in use. Killing existing process..."
        lsof -ti :$port | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# Function to kill all processes if one fails
cleanup() {
    echo "Error occurred. Cleaning up..."
    if [ -f .pid ]; then
        while read pid; do
            if [ ! -z "$pid" ]; then
                kill $pid 2>/dev/null
            fi
        done < .pid
    fi
    rm -f .pid
    exit 1
}

# Function to stop existing processes
stop_existing() {
    echo "Stopping any existing RAGme processes..."
    if [ -f .pid ]; then
        while read pid; do
            if [ ! -z "$pid" ]; then
                echo "Stopping existing process $pid..."
                kill $pid 2>/dev/null
            fi
        done < .pid
        rm -f .pid
        sleep 2
    fi
    
    # Also kill any processes using our ports
    check_port 8020  # UI
    check_port 8021  # API
    check_port 8022  # MCP
}

# Set up error handling
trap cleanup ERR

# Stop any existing processes first
stop_existing

# Create a clean PID file
echo "" > .pid

# Start api.py
echo "Starting api.py..."
uv run uvicorn src.ragme.api:app --reload --host 0.0.0.0 --port 8021 &
echo $! >> .pid
sleep 3

# Start mcp.py
echo "Starting mcp.py..."
uv run uvicorn src.ragme.mcp:app --reload --host 0.0.0.0 --port 8022 &
echo $! >> .pid
sleep 3

# Start local_agent.py
echo "Starting local_agent.py..."
uv run python -m src.ragme.local_agent &
echo $! >> .pid
sleep 3

# Start ui.py
echo "Starting ui.py..."
PYTHONPATH=$PYTHONPATH:$(pwd) uv run streamlit run src/ragme/ui.py --server.port 8020 &
echo $! >> .pid

echo "All RAGme processes started successfully!"
echo "Use ./stop.sh to stop all RAGme processes" 