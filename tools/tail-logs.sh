#!/bin/bash

# RAGme Log Tailing Script
# Usage: ./tools/tail-logs.sh [all|api|mcp|agent|frontend|status|recent]

# Colors for different services
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local port=$1
    local service_name=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name is running on port $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is not running on port $port${NC}"
        return 1
    fi
}

# Function to get the actual agent PID (more specific)
get_agent_pid() {
    # Look for the specific local_agent process
    pgrep -f "python -m src.ragme.local_agent" | head -1
}

# Function to show all service status
show_status() {
    echo -e "${BLUE}=== RAGme Service Status ===${NC}"
    echo ""
    check_service 3020 "New Frontend"
    check_service 8021 "API"
    check_service 8022 "MCP"
    
    local agent_pid=$(get_agent_pid)
    if [ ! -z "$agent_pid" ]; then
        echo -e "${GREEN}✅ Agent is running (PID: $agent_pid)${NC}"
    else
        echo -e "${RED}❌ Agent is not running${NC}"
    fi
    echo ""
}

# Function to show recent logs
show_recent_logs() {
    echo -e "${BLUE}=== Recent System Logs (Last 50 lines) ===${NC}"
    echo ""
    
    # Show recent system logs that might be related to RAGme
    echo -e "${YELLOW}Recent system logs containing 'ragme', 'uvicorn', 'streamlit', or 'node':${NC}"
    log show --predicate 'eventMessage CONTAINS "ragme" OR eventMessage CONTAINS "uvicorn" OR eventMessage CONTAINS "streamlit" OR eventMessage CONTAINS "node"' --last 5m 2>/dev/null | tail -50 | while read line; do
        echo "[SYS] $line"
    done
    
    echo ""
    echo -e "${YELLOW}Recent application logs:${NC}"
    log show --predicate 'processImagePath CONTAINS "ragme"' --last 5m 2>/dev/null | tail -20 | while read line; do
        echo "[APP] $line"
    done
}

# Function to monitor system logs for RAGme processes
monitor_system_logs() {
    local service_name=$1
    local service_tag=$2
    local pid=$3
    
    echo -e "${YELLOW}Monitoring system logs for $service_name (PID: $pid)...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
    echo ""
    
    # Monitor system logs for the specific process
    log stream --predicate "process == '$pid'" 2>/dev/null | while read line; do
        echo "[$service_tag] $line"
    done
}

# Function to tail API logs
tail_api_logs() {
    echo -e "${BLUE}📡 Tailing API logs (port 8021)...${NC}"
    if check_service 8021 "API"; then
        if [ -f "logs/api.log" ]; then
            echo -e "${BLUE}Following API log file...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
            echo ""
            tail -f logs/api.log
        else
            echo -e "${RED}❌ API log file not found (logs/api.log)${NC}"
            echo -e "${YELLOW}API may not be running or log file not created${NC}"
        fi
    fi
}

# Function to tail MCP logs
tail_mcp_logs() {
    echo -e "${BLUE}📡 Tailing MCP logs (port 8022)...${NC}"
    if check_service 8022 "MCP"; then
        if [ -f "logs/mcp.log" ]; then
            echo -e "${BLUE}Following MCP log file...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
            echo ""
            tail -f logs/mcp.log
        else
            echo -e "${RED}❌ MCP log file not found (logs/mcp.log)${NC}"
        fi
    fi
}

# Function to tail agent logs
tail_agent_logs() {
    echo -e "${BLUE}📡 Tailing Agent logs...${NC}"
    local agent_pid=$(get_agent_pid)
    if [ ! -z "$agent_pid" ]; then
        if [ -f "logs/agent.log" ]; then
            echo -e "${BLUE}Following Agent log file...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
            echo ""
            tail -f logs/agent.log
        else
            echo -e "${RED}❌ Agent log file not found (logs/agent.log)${NC}"
        fi
    else
        echo -e "${RED}❌ Agent is not running${NC}"
    fi
}

# Function to tail frontend logs
tail_frontend_logs() {
    echo -e "${BLUE}📡 Tailing Frontend logs (port 3020)...${NC}"
    if check_service 3020 "New Frontend"; then
        if [ -f "logs/frontend.log" ]; then
            echo -e "${BLUE}Following Frontend log file...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
            echo ""
            tail -f logs/frontend.log
        else
            echo -e "${RED}❌ Frontend log file not found (logs/frontend.log)${NC}"
        fi
    fi
}

# Function to tail all logs
tail_all_logs() {
    echo -e "${BLUE}📡 Tailing all service logs...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
    echo ""
    
    # Use tail -f with multiple log files
    if [ -f "logs/api.log" ] && [ -f "logs/mcp.log" ] && [ -f "logs/agent.log" ] && [ -f "logs/frontend.log" ]; then
        tail -f logs/api.log logs/mcp.log logs/agent.log logs/frontend.log
    else
        echo -e "${YELLOW}⚠️ Some log files not found. Starting services may not have created logs yet.${NC}"
        echo -e "${YELLOW}Available log files:${NC}"
        ls -la logs/ 2>/dev/null || echo "No logs directory found"
    fi
}

# Function to show help
show_help() {
    echo -e "${BLUE}RAGme Log Tailing Script${NC}"
    echo ""
    echo "Usage: $0 [all|api|mcp|agent|frontend|status|recent]"
    echo ""
    echo "Commands:"
    echo -e "  ${GREEN}all${NC}        - Tail logs from all running services"
    echo -e "  ${GREEN}api${NC}        - Tail API logs (port 8021)"
    echo -e "  ${GREEN}mcp${NC}        - Tail MCP logs (port 8022)"
    echo -e "  ${GREEN}agent${NC}      - Tail Agent logs"
    echo -e "  ${GREEN}frontend${NC}   - Tail Frontend logs (port 3020)"
    echo -e "  ${GREEN}status${NC}     - Show status of all services"
    echo -e "  ${GREEN}recent${NC}     - Show recent logs"
    echo ""
    echo "Examples:"
    echo "  $0 all           # Tail all service logs"
    echo "  $0 api           # Tail only API logs"
    echo "  $0 status        # Show service status"
    echo "  $0 recent        # Show recent logs"
    echo ""
    echo "Note: This script tails real-time logs from RAGme services using system log monitoring."
}

# Main script logic
case "${1:-all}" in
    "all")
        tail_all_logs
        ;;
    "api")
        tail_api_logs
        ;;
    "mcp")
        tail_mcp_logs
        ;;
    "agent")
        tail_agent_logs
        ;;
    "frontend")
        tail_frontend_logs
        ;;
    "status")
        show_status
        ;;
    "recent")
        show_recent_logs
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac 