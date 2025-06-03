#!/bin/bash

if [ ! -f .pid ]; then
    echo "No .pid file found. No processes to stop."
    exit 0
fi

echo "Stopping all processes..."
while read pid; do
    if [ ! -z "$pid" ]; then
        echo "Stopping process $pid..."
        kill $pid 2>/dev/null
    fi
done < .pid

# Remove the PID file
rm -f .pid
echo "All processes stopped." 