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

# Start ragme_api.py
echo "Starting ragme_api.py..."
uv run uvicorn ragme_api:app --reload --host 0.0.0.0 --port 8021 &
echo $! >> .pid
sleep 2

# Start ragme-mcp.py
echo "Starting ragme_mcp.py..."
uv run uvicorn ragme_mcp:app --reload --host 0.0.0.0 --port 8022 &
echo $! >> .pid
sleep 2

# Start ragme-agent.py
echo "Starting ragme_agent.py..."
uv run python ragme_agent.py &
echo $! >> .pid
sleep 2

# Start ragme-ui.py
echo "Starting ragme_ui.py..."
uv run streamlit run ragme_ui.py --server.port 8020 &
echo $! >> .pid

echo "All RAGme processes started successfully!"
echo "Use ./stop.sh to stop all RAGme processes" 