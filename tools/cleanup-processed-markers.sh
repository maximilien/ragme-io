#!/bin/bash

# Cleanup script for RAGme processed marker files
# This script removes .processed files that are older than 60 seconds

echo "Cleaning up old processed marker files..."

# Find and remove .processed files older than 60 seconds in watch_directory
if [ -d "./watch_directory" ]; then
    find ./watch_directory -name "*.processed" -type f -mmin +1 -delete
    echo "Cleaned up processed markers in watch_directory"
else
    echo "watch_directory not found"
fi

echo "Cleanup completed!"
