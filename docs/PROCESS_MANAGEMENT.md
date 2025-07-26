# Process Management

RAGme AI uses a comprehensive process management system to handle multiple services. The `./stop.sh` script has been enhanced to provide full process lifecycle management.

## 🚀 Quick Start

```bash
# Start all services (new frontend by default)
./start.sh

# Start with legacy UI
./start.sh legacy-ui

# Check status
./stop.sh status

# Restart all services
./stop.sh restart

# Stop all services
./stop.sh stop
```

## 📋 Available Commands

### `./start.sh` (Default)
Starts all RAGme services with the new frontend:
- Starts API server (port 8021)
- Starts MCP server (port 8022)
- Starts file monitoring agent
- Starts new frontend (port 3020)
- Provides status feedback

### `./start.sh legacy-ui`
Starts all RAGme services with the legacy Streamlit UI:
- Starts API server (port 8021)
- Starts MCP server (port 8022)
- Starts file monitoring agent
- Starts legacy Streamlit UI (port 8020)
- Provides status feedback

### `./start.sh restart-frontend`
Restarts only the new frontend service:
- Stops existing frontend process
- Rebuilds and starts new frontend
- Keeps other services running

### `./stop.sh` or `./stop.sh stop`
Stops all RAGme processes:
- Kills processes from PID file
- Forces kill processes on ports 3020, 8020, 8021, 8022
- Cleans up PID file
- Verifies all processes are stopped

### `./stop.sh restart`
Restarts all RAGme processes:
- Stops existing processes
- Waits for cleanup
- Starts all services using `./start.sh`
- Provides status feedback

### `./stop.sh status`
Shows comprehensive status of all services:
- PID file status and process validation
- Port status for each service
- Service URLs when running
- Helpful status messages

### `./stop.sh legacy-ui`
Stops only the legacy UI process:
- Kills legacy UI process on port 8020
- Removes legacy UI PID from PID file
- Keeps other services running

## 🔧 Service Architecture

RAGme AI runs five main services:

| Service | Port | Description | URL | Default |
|---------|------|-------------|-----|---------|
| New Frontend | 3020 | Modern web interface with three-pane layout | http://localhost:3020 | ✅ **YES** |
| Legacy Streamlit UI | 8020 | Original web interface | http://localhost:8020 | ❌ NO |
| FastAPI | 8021 | REST API | http://localhost:8021 | ✅ **YES** |
| MCP | 8022 | Model Context Protocol | http://localhost:8022 | ✅ **YES** |
| Local Agent | - | File monitoring | Background process | ✅ **YES** |

## 🛠️ Troubleshooting

### Services Not Starting
```bash
# Check if ports are in use
./stop.sh status

# Force restart
./stop.sh restart

# Check logs in terminal where services were started
```

### Stale PID Files
```bash
# The status command will show stale PIDs
./stop.sh status

# Restart will clean up stale PIDs
./stop.sh restart
```

### Port Conflicts
```bash
# Check what's using the ports
lsof -i :3020  # New Frontend
lsof -i :8020  # Legacy UI
lsof -i :8021  # API
lsof -i :8022  # MCP

# Kill conflicting processes
./stop.sh stop
```

### Frontend Issues
```bash
# Restart frontend only
./start.sh restart-frontend

# Check frontend logs
./tools/tail-logs.sh frontend

# Rebuild frontend
cd frontend
npm run build
npm start
```

## 📊 Status Output Examples

### All Services Running (New Frontend)
```
=== RAGme Process Status ===

📄 PID File Status:
   PID file exists with the following processes:
   ✅ Process 12345 is running
   ✅ Process 12346 is running
   ✅ Process 12347 is running
   ✅ Process 12348 is running

🌐 Port Status:
   ✅ New Frontend (port 3020) - Running (PID: 12345)
   ✅ FastAPI (port 8021) - Running (PID: 12346)
   ✅ MCP (port 8022) - Running (PID: 12347)

🎉 All RAGme services are running!
   • New Frontend: http://localhost:3020
   • API: http://localhost:8021
   • MCP: http://localhost:8022
```

### All Services Running (Legacy UI)
```
=== RAGme Process Status ===

📄 PID File Status:
   PID file exists with the following processes:
   ✅ Process 12345 is running
   ✅ Process 12346 is running
   ✅ Process 12347 is running
   ✅ Process 12348 is running

🌐 Port Status:
   ✅ Legacy Streamlit UI (port 8020) - Running (PID: 12345)
   ✅ FastAPI (port 8021) - Running (PID: 12346)
   ✅ MCP (port 8022) - Running (PID: 12347)

🎉 All RAGme services are running!
   • Legacy UI: http://localhost:8020
   • API: http://localhost:8021
   • MCP: http://localhost:8022
```

### Some Services Down
```
=== RAGme Process Status ===

📄 PID File Status:
   PID file exists with the following processes:
   ✅ Process 12345 is running
   ❌ Process 12346 is not running (stale PID)

🌐 Port Status:
   ✅ New Frontend (port 3020) - Running (PID: 12345)
   ❌ FastAPI (port 8021) - Not running
   ❌ MCP (port 8022) - Not running

⚠️  Some RAGme services are not running.
   Use './stop.sh restart' to restart all services.
```

## 🔄 Integration with CI/CD

The process management system integrates with CI/CD pipelines:

```yaml
# Example CI step
- name: Restart services
  run: |
    chmod +x stop.sh
    ./stop.sh restart
```

## 📝 Best Practices

1. **Always use status first**: Check service status before making changes
2. **Use restart for updates**: Restart services after code changes
3. **Monitor PID files**: The system automatically manages PID files
4. **Check logs**: Monitor service logs for debugging
5. **Port management**: The system automatically handles port conflicts
6. **Frontend development**: Use `./start.sh restart-frontend` for frontend changes
7. **Legacy UI**: Use `./start.sh legacy-ui` when you need the old interface

## 🚨 Emergency Procedures

### Force Kill All Processes
```bash
# If normal stop doesn't work
pkill -f "ragme"
pkill -f "streamlit"
pkill -f "uvicorn"
pkill -f "node"
```

### Reset Everything
```bash
# Complete reset
rm -f .pid
./stop.sh stop
./start.sh
```

### Frontend Reset
```bash
# Reset frontend only
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
cd ..
./start.sh restart-frontend
```

## 🔍 Debugging

### Check Service Status
```bash
./stop.sh status
```

This will show:
- Which processes are running
- Port status for each service
- PID information for debugging

### View Logs
Services log to the terminal where they were started. Check for:
- Connection errors
- Configuration issues
- Import errors

### Monitor Logs in Real-time
```bash
# Monitor all services
./tools/tail-logs.sh all

# Monitor specific services
./tools/tail-logs.sh api
./tools/tail-logs.sh mcp
./tools/tail-logs.sh frontend
./tools/tail-logs.sh legacy-ui
```

### Test Individual Components
```bash
# Test API
curl --max-time 10 http://localhost:8021/docs

# Test MCP
curl --max-time 10 http://localhost:8022/docs

# Test new frontend
open http://localhost:3020

# Test legacy UI
open http://localhost:8020
```

## 🎯 Service-Specific Management

### New Frontend Management
```bash
# Start with new frontend (default)
./start.sh

# Restart frontend only
./start.sh restart-frontend

# Check frontend status
./stop.sh status | grep "3020"

# Monitor frontend logs
./tools/tail-logs.sh frontend
```

### Legacy UI Management
```bash
# Start with legacy UI
./start.sh legacy-ui

# Stop legacy UI only
./stop.sh legacy-ui

# Check legacy UI status
./stop.sh status | grep "8020"

# Monitor legacy UI logs
./tools/tail-logs.sh legacy-ui
```

### Core Services Management
```bash
# Check core services
./stop.sh status | grep -E "(8021|8022)"

# Monitor API logs
./tools/tail-logs.sh api

# Monitor MCP logs
./tools/tail-logs.sh mcp

# Monitor agent logs
./tools/tail-logs.sh agent
```

## 📈 Performance Monitoring

### Resource Usage
```bash
# Check process resource usage
ps aux | grep -E "(ragme|streamlit|uvicorn|node)" | grep -v grep

# Check port usage
lsof -i :3020 -i :8020 -i :8021 -i :8022
```

### Memory and CPU
```bash
# Monitor system resources
top -p $(pgrep -f "ragme|streamlit|uvicorn|node" | tr '\n' ',' | sed 's/,$//')
```

## 🔧 Configuration

### Environment Variables
The process management system respects these environment variables:
- `RAGME_API_URL`: API server URL (default: http://localhost:8021)
- `RAGME_MCP_URL`: MCP server URL (default: http://localhost:8022)
- `VECTOR_DB_TYPE`: Vector database type (default: milvus)

### PID File Management
The system uses a `.pid` file to track running processes:
- Created when services start
- Cleaned up when services stop
- Validated during status checks
- Used for graceful shutdowns

### Port Management
The system manages these ports:
- **3020**: New frontend (default)
- **8020**: Legacy UI (optional)
- **8021**: API server (required)
- **8022**: MCP server (required)

## 🚀 Quick Reference

### Common Commands
```bash
# Start services
./start.sh              # New frontend (default)
./start.sh legacy-ui    # Legacy UI

# Stop services
./stop.sh               # Stop all
./stop.sh legacy-ui     # Stop legacy UI only

# Restart services
./stop.sh restart       # Restart all
./start.sh restart-frontend  # Restart frontend only

# Check status
./stop.sh status        # Show all status
./tools/tail-logs.sh status  # Show service status

# Monitor logs
./tools/tail-logs.sh all     # All services
./tools/tail-logs.sh frontend # Frontend only
```

### Service URLs
- **New Frontend**: http://localhost:3020 (default)
- **Legacy UI**: http://localhost:8020
- **API Docs**: http://localhost:8021/docs
- **MCP Docs**: http://localhost:8022/docs 