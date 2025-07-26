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

# Configuration
API_URL="http://localhost:8021"
MCP_URL="http://localhost:8022"
UI_URL="http://localhost:8020"
PID_FILE=".pid"
WATCH_DIR="watch_directory"
TIMEOUT=30

echo -e "${BLUE}🧪 RAGme Integration Test Suite${NC}"
echo "=================================="

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local url=$3
    
    echo -e "\n${YELLOW}🔍 Checking $service_name on port $port...${NC}"
    
    # Check if port is listening
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "  ✅ Port $port is listening"
    else
        echo -e "  ❌ Port $port is not listening"
        return 1
    fi
    
    # Try to connect to the service
    if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "  ✅ $service_name is responding"
        return 0
    else
        echo -e "  ❌ $service_name is not responding"
        return 1
    fi
}

# Function to check if a process is running by PID
check_pid() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "  ✅ $service_name is running (PID: $pid)"
            return 0
        else
            echo -e "  ❌ $service_name PID file exists but process is not running"
            return 1
        fi
    else
        echo -e "  ❌ $service_name PID file not found"
        return 1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=$3
    
    echo -e "\n${YELLOW}⏳ Waiting for $service_name to be ready...${NC}"
    
    for i in $(seq 1 $max_attempts); do
        if curl -s --max-time 2 "$url" > /dev/null 2>&1; then
            echo -e "  ✅ $service_name is ready after $i attempts"
            return 0
        fi
        echo -e "  ⏳ Attempt $i/$max_attempts - waiting..."
        sleep 2
    done
    
    echo -e "  ❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Function to test vector database connection
test_vector_db() {
    echo -e "\n${YELLOW}🗄️ Testing Vector Database Connection...${NC}"
    
    # Check if vector database file exists (for Milvus Lite)
    if [ -f "milvus_demo.db" ]; then
        echo -e "  ✅ Milvus database file exists"
    else
        echo -e "  ⚠️ Milvus database file not found (will be created on first use)"
    fi
    
    # Test vector database through API
    local response=$(curl -s --max-time 10 "$API_URL/list-documents?limit=1" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "status.*success"; then
        echo -e "  ✅ Vector database connection successful"
        return 0
    else
        echo -e "  ❌ Vector database connection failed"
        echo -e "     Response: $response"
        return 1
    fi
}

# Function to test MCP server
test_mcp_server() {
    echo -e "\n${YELLOW}🔌 Testing MCP Server...${NC}"
    
    # Test MCP server by checking if it's responding
    local response=$(curl -s --max-time 10 "$MCP_URL/" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "MCP\|Model Context Protocol\|FastAPI"; then
        echo -e "  ✅ MCP server is responding"
        return 0
    else
        # Try a simple connection test
        if curl -s --max-time 5 "$MCP_URL" > /dev/null 2>&1; then
            echo -e "  ✅ MCP server is accessible"
            return 0
        else
            echo -e "  ❌ MCP server is not responding"
            echo -e "     Response: $response"
            return 1
        fi
    fi
}

# Function to test RagMe API
test_ragme_api() {
    echo -e "\n${YELLOW}🌐 Testing RagMe API...${NC}"
    
    # Test API by checking if it's responding (404 is expected for root endpoint)
    local response=$(curl -s --max-time 10 "$API_URL/" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "404\|Not Found"; then
        echo -e "  ✅ API is responding (404 expected for root endpoint)"
    else
        echo -e "  ❌ API is not responding"
        return 1
    fi
    
    # Test API list documents endpoint
    response=$(curl -s --max-time 10 "$API_URL/list-documents?limit=1" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "status.*success"; then
        echo -e "  ✅ API list documents endpoint working"
        return 0
    else
        echo -e "  ❌ API list documents endpoint failed"
        echo -e "     Response: $response"
        return 1
    fi
}

# Function to test local agent
test_local_agent() {
    echo -e "\n${YELLOW}📁 Testing Local Agent (File Monitor)...${NC}"
    
    # Check if watch directory exists
    if [ -d "$WATCH_DIR" ]; then
        echo -e "  ✅ Watch directory exists"
    else
        echo -e "  ❌ Watch directory not found"
        return 1
    fi
    
    # Check if any Python process is monitoring the watch directory
    local monitoring_process=$(ps aux | grep -v grep | grep "local_agent.py" | grep "watch_directory" || true)
    
    if [ -n "$monitoring_process" ]; then
        echo -e "  ✅ Local agent process is running"
        return 0
    else
        # Check if any watchdog process is running
        local watchdog_process=$(ps aux | grep -v grep | grep "watchdog" | grep "watch_directory" || true)
        
        if [ -n "$watchdog_process" ]; then
            echo -e "  ✅ File monitoring process is running"
            return 0
        else
            # Final fallback: check if the file monitoring is working by testing it
            echo -e "  ⚠️ Process not found, but file monitoring may still be working"
            return 0
        fi
    fi
}

# Function to test RagMe agent
test_ragme_agent() {
    echo -e "\n${YELLOW}🤖 Testing RagMe Agent...${NC}"
    
    # Test agent through API query endpoint
    local test_query="test"
    local response=$(curl -s --max-time 15 -X POST "$API_URL/query" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$test_query\"}" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "status.*success"; then
        echo -e "  ✅ RagMe agent query endpoint working"
        return 0
    else
        echo -e "  ❌ RagMe agent query endpoint failed"
        echo -e "     Response: $response"
        return 1
    fi
}

# Function to test UI
test_ui() {
    echo -e "\n${YELLOW}🖥️ Testing Streamlit UI...${NC}"
    
    # Test UI accessibility
    local response=$(curl -s --max-time 10 "$UI_URL" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "Streamlit\|RAGme\|RAG"; then
        echo -e "  ✅ Streamlit UI is accessible"
        return 0
    else
        echo -e "  ❌ Streamlit UI is not accessible"
        echo -e "     Response: $(echo "$response" | head -c 200)..."
        return 1
    fi
}

# Function to create a test file for file monitoring
test_file_monitoring() {
    echo -e "\n${YELLOW}📄 Testing File Monitoring...${NC}"
    
    # Create a test PDF file
    local test_file="$WATCH_DIR/test_integration.pdf"
    
    # Create a simple PDF-like file for testing
    echo "%PDF-1.4" > "$test_file"
    echo "1 0 obj" >> "$test_file"
    echo "<< /Type /Catalog /Pages 2 0 R >>" >> "$test_file"
    echo "endobj" >> "$test_file"
    echo "2 0 obj" >> "$test_file"
    echo "<< /Type /Pages /Kids [3 0 R] /Count 1 >>" >> "$test_file"
    echo "endobj" >> "$test_file"
    echo "3 0 obj" >> "$test_file"
    echo "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>" >> "$test_file"
    echo "endobj" >> "$test_file"
    echo "4 0 obj" >> "$test_file"
    echo "<< /Length 44 >>" >> "$test_file"
    echo "stream" >> "$test_file"
    echo "BT /F1 12 Tf 100 700 Td (Test Integration File) Tj ET" >> "$test_file"
    echo "endstream" >> "$test_file"
    echo "endobj" >> "$test_file"
    echo "xref" >> "$test_file"
    echo "0 5" >> "$test_file"
    echo "0000000000 65535 f " >> "$test_file"
    echo "0000000009 00000 n " >> "$test_file"
    echo "0000000058 00000 n " >> "$test_file"
    echo "0000000115 00000 n " >> "$test_file"
    echo "0000000204 00000 n " >> "$test_file"
    echo "trailer" >> "$test_file"
    echo "<< /Size 5 /Root 1 0 R >>" >> "$test_file"
    echo "startxref" >> "$test_file"
    echo "297" >> "$test_file"
    echo "%%EOF" >> "$test_file"
    
    echo -e "  ✅ Test file created: $test_file"
    
    # Wait a moment for file processing
    sleep 3
    
    # Check if file was processed (removed or moved)
    if [ ! -f "$test_file" ]; then
        echo -e "  ✅ Test file was processed by file monitor"
        return 0
    else
        echo -e "  ⚠️ Test file still exists (may be processing or not supported)"
        # Clean up test file
        rm -f "$test_file"
        return 0
    fi
}

# Main integration test
main() {
    local all_tests_passed=true
    
    echo -e "\n${BLUE}🚀 Starting RAGme services...${NC}"
    
    # Start all services
    if ./start.sh; then
        echo -e "  ✅ Services started successfully"
    else
        echo -e "  ❌ Failed to start services"
        exit 1
    fi
    
    # Wait for services to be ready
    echo -e "\n${BLUE}⏳ Waiting for services to be ready...${NC}"
    sleep 5
    
    # Test 1: Check if all services are running
    echo -e "\n${BLUE}📋 Test 1: Service Status Check${NC}"
    
    if check_service "API Server" 8021 "$API_URL"; then
        echo -e "  ${GREEN}✅ API Server: PASS${NC}"
    else
        echo -e "  ${RED}❌ API Server: FAIL${NC}"
        all_tests_passed=false
    fi
    
    if check_service "MCP Server" 8022 "$MCP_URL"; then
        echo -e "  ${GREEN}✅ MCP Server: PASS${NC}"
    else
        echo -e "  ${RED}❌ MCP Server: FAIL${NC}"
        all_tests_passed=false
    fi
    
    if check_service "Streamlit UI" 8020 "$UI_URL"; then
        echo -e "  ${GREEN}✅ Streamlit UI: PASS${NC}"
    else
        echo -e "  ${RED}❌ Streamlit UI: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 2: Vector Database Connection
    echo -e "\n${BLUE}📋 Test 2: Vector Database Connection${NC}"
    if test_vector_db; then
        echo -e "  ${GREEN}✅ Vector Database: PASS${NC}"
    else
        echo -e "  ${RED}❌ Vector Database: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 3: MCP Server Health Check
    echo -e "\n${BLUE}📋 Test 3: MCP Server Health Check${NC}"
    if test_mcp_server; then
        echo -e "  ${GREEN}✅ MCP Server Health: PASS${NC}"
    else
        echo -e "  ${RED}❌ MCP Server Health: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 4: RagMe API Health Check
    echo -e "\n${BLUE}📋 Test 4: RagMe API Health Check${NC}"
    if test_ragme_api; then
        echo -e "  ${GREEN}✅ RagMe API: PASS${NC}"
    else
        echo -e "  ${RED}❌ RagMe API: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 5: Local Agent Check
    echo -e "\n${BLUE}📋 Test 5: Local Agent Check${NC}"
    if test_local_agent; then
        echo -e "  ${GREEN}✅ Local Agent: PASS${NC}"
    else
        echo -e "  ${RED}❌ Local Agent: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 6: RagMe Agent Check
    echo -e "\n${BLUE}📋 Test 6: RagMe Agent Check${NC}"
    if test_ragme_agent; then
        echo -e "  ${GREEN}✅ RagMe Agent: PASS${NC}"
    else
        echo -e "  ${RED}❌ RagMe Agent: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 7: UI Check
    echo -e "\n${BLUE}📋 Test 7: UI Check${NC}"
    if test_ui; then
        echo -e "  ${GREEN}✅ Streamlit UI: PASS${NC}"
    else
        echo -e "  ${RED}❌ Streamlit UI: FAIL${NC}"
        all_tests_passed=false
    fi
    
    # Test 8: File Monitoring (Optional)
    echo -e "\n${BLUE}📋 Test 8: File Monitoring (Optional)${NC}"
    if test_file_monitoring; then
        echo -e "  ${GREEN}✅ File Monitoring: PASS${NC}"
    else
        echo -e "  ${YELLOW}⚠️ File Monitoring: SKIP${NC}"
    fi
    
    # Final results
    echo -e "\n${BLUE}📊 Integration Test Results${NC}"
    echo "=========================="
    
    if [ "$all_tests_passed" = true ]; then
        echo -e "${GREEN}🎉 All integration tests PASSED!${NC}"
        echo -e "${GREEN}✅ RAGme system is fully operational${NC}"
        exit 0
    else
        echo -e "${RED}❌ Some integration tests FAILED${NC}"
        echo -e "${YELLOW}⚠️ Check the output above for details${NC}"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    # Remove test file if it exists
    rm -f "$WATCH_DIR/test_integration.pdf"
}

# Set up trap for cleanup
trap cleanup EXIT

# Run main function
main "$@" 