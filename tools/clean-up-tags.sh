#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[CLEAR-TAGS]${NC} $1"
}

# Check if tags.txt exists
TAGS_FILE="./tags.txt"

if [ ! -f "$TAGS_FILE" ]; then
    print_error "Tags file not found: $TAGS_FILE"
    echo ""
    echo "The tags.txt file does not exist in the current directory."
    echo "This script is designed to clear an existing tags file."
    echo ""
    echo "If you want to create a new tags file, you can do so manually:"
    echo "  touch tags.txt"
    echo ""
    echo "Or if you're looking for a different tags file, please check the path."
    exit 1
fi

# Check if the file is empty
if [ ! -s "$TAGS_FILE" ]; then
    print_warning "Tags file is already empty: $TAGS_FILE"
    echo "No action needed."
    exit 0
fi

# Show current content before clearing
print_header "Current tags file content:"
echo "================================"
cat "$TAGS_FILE"
echo "================================"
echo ""

# Clear the file
print_status "Clearing tags file: $TAGS_FILE"
> "$TAGS_FILE"

# Verify the file is now empty
if [ -s "$TAGS_FILE" ]; then
    print_error "Failed to clear tags file. File still contains content."
    exit 1
else
    print_status "Successfully cleared tags file: $TAGS_FILE"
    echo "The file is now empty and ready for new tags."
fi
