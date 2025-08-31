#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

set -e

echo "🔍 Running Go linter and formatter on deployment files..."

# Check if Go is available
if ! command -v go >/dev/null 2>&1; then
    echo "❌ Go not found. Please install Go to run Go linting."
    exit 1
fi

# Check if deployment directory exists
if [ ! -d "deployment" ]; then
    echo "❌ Deployment directory not found."
    exit 1
fi

cd deployment

# Find all Go files
echo "📁 Found Go files:"
find . -name "*.go" -type f | while read -r file; do
    echo "  - $file"
done

# Run go fmt on each directory that contains Go files
echo "🎨 Formatting Go code..."
directories=$(find . -name "*.go" -type f -exec dirname {} \; | sort -u)
for dir in $directories; do
    if [ -d "$dir" ]; then
        echo "  Formatting $dir..."
        # Check if this directory has a go.mod file or is part of a Go module
        if [ -f "$dir/go.mod" ] || [ -f "go.mod" ]; then
            (cd "$dir" && go fmt ./...)
        else
            # For directories without go.mod, format individual files
            find "$dir" -name "*.go" -type f -exec go fmt {} \;
        fi
    fi
done
echo "✅ Go formatting completed!"

# Run go vet on all Go packages
echo "🔍 Running Go vet on all packages..."
if [ -d "operator" ]; then
    cd operator
    if go vet ./...; then
        echo "✅ Go vet checks passed!"
    else
        echo "❌ Go vet failed"
        exit 1
    fi
    cd ..
else
    echo "⚠️  Operator directory not found, skipping go vet"
fi

# Check for any unformatted files
echo "🔍 Checking for unformatted Go files..."
unformatted=$(gofmt -l .)
if [ -n "$unformatted" ]; then
    echo "❌ Found unformatted Go files:"
    echo "$unformatted"
    echo "Please run 'go fmt ./...' to format these files"
    exit 1
else
    echo "✅ All Go files are properly formatted!"
fi

# Run go mod tidy if go.mod exists
if [ -f "operator/go.mod" ]; then
    echo "📦 Running go mod tidy..."
    cd operator
    if go mod tidy; then
        echo "✅ Go mod tidy completed!"
    else
        echo "❌ Go mod tidy failed"
        exit 1
    fi
    cd ..
fi

# Optional: Run go test if requested
if [ "$1" = "--test" ]; then
    echo "🧪 Running Go tests..."
    if [ -d "operator" ]; then
        cd operator
        if go test ./...; then
            echo "✅ Go tests passed!"
        else
            echo "❌ Go tests failed"
            exit 1
        fi
        cd ..
    else
        echo "⚠️  Operator directory not found, skipping tests"
    fi
fi

cd ..

echo "🎯 Go code quality checks completed successfully!"
