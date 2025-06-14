#!/bin/bash

# Create a clean PID file
echo "" > .pid

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

# Set up error handling
trap cleanup ERR

# Start api.py
echo "Starting api.py..."
uv run uvicorn src.ragme.api:app --reload --host 0.0.0.0 --port 8021 &
echo $! >> .pid
sleep 2

# Start mcp.py
echo "Starting mcp.py..."
uv run uvicorn src.ragme.mcp:app --reload --host 0.0.0.0 --port 8022 &
echo $! >> .pid
sleep 2

# Start agent.py
echo "Starting agent.py..."
uv run python -m src.ragme.agent &
echo $! >> .pid
sleep 2

# Start ui.py
echo "Starting ui.py..."
PYTHONPATH=$PYTHONPATH:$(pwd) uv run streamlit run src/ragme/ui.py --server.port 8020 &
echo $! >> .pid

echo "All RAGme processes started successfully!"
echo "Use ./stop.sh to stop all RAGme processes" 