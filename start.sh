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

# Start ragme-api.py
echo "Starting ragme-api.py..."
uv run uvicorn ragme-api:app --reload --host 0.0.0.0 --port 8000 &
echo $! >> .pid
sleep 2

# Start ragme-mcp.py
echo "Starting ragme-mcp.py..."
uv run uvicorn ragme-mcp:app --reload --host 0.0.0.0 --port 8000 &
echo $! >> .pid
sleep 2

# Start ragme-agent.py
echo "Starting ragme-agent.py..."
uv run python ragme-agent.py &
echo $! >> .pid
sleep 2

# Start ragme-ui.py
echo "Starting ragme-ui.py..."
uv run streamlit run ragme-ui.py &
echo $! >> .pid

echo "All RAGme processes started successfully!"
echo "Use ./stop.sh to stop all RAGme processes" 