#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

set -e

echo "🔍 Running TypeScript linter on frontend files..."

# Check if we're in the frontend directory or need to navigate there
if [ -d "frontend" ]; then
    echo "📁 Checking TypeScript files..."
    cd frontend
    
    echo "🔍 Running ESLint..."
    npm run lint
    
    echo "🎨 Checking code formatting with Prettier..."
    npm run format
    
    cd ..
    echo "✅ TypeScript linting checks passed!"
    echo "✨ TypeScript formatting checks passed!"
else
    echo "❌ Frontend directory not found!"
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "🎯 TypeScript code quality checks completed successfully!" 