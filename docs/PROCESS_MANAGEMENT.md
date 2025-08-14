# Process Management

RAGme AI uses a comprehensive process management system to handle multiple services. The `./stop.sh` script has been enhanced to provide full process lifecycle management.

## 🚀 Quick Start

```bash
# Start all services (new frontend by default)
./start.sh

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
- Starts new frontend (port 8020)
- Provides status feedback

### `./start.sh restart-frontend`
Restarts only the new frontend service:
- Stops existing frontend process
- Rebuilds and starts new frontend
- Keeps other services running

### `./stop.sh` or `./stop.sh stop`
Stops all RAGme processes:
- Kills processes from PID file
- Forces kill processes on ports 8020, 8021, 8022
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

## 🔧 Service Architecture

RAGme.io runs four main services:

| Service | Port | Description | URL | Default |
|---------|------|-------------|-----|---------|
| New Frontend | 8020 | Modern web interface with three-pane layout | http://localhost:8020 | ✅ **YES** |
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
lsof -i :8020  # New Frontend
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
   ✅ New Frontend (port 8020) - Running (PID: 12345)
   ✅ FastAPI (port 8021) - Running (PID: 12346)
   ✅ MCP (port 8022) - Running (PID: 12347)

🎉 All RAGme services are running!
   • New Frontend: http://localhost:8020
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
   ✅ New Frontend (port 8020) - Running (PID: 12345)
   ❌ FastAPI (port 8021) - Not running
   ❌ MCP (port 8022) - Not running

⚠️  Some RAGme services are not running.
   Use './stop.sh restart' to restart all services.
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
```

### Test Individual Components
```bash
# Test API
curl --max-time 10 http://localhost:8021/docs

# Test MCP
curl --max-time 10 http://localhost:8022/docs

# Test new frontend
open http://localhost:8020
```

## 🚨 Emergency Procedures

### Force Kill All Processes
```bash
# If normal stop doesn't work
pkill -f "ragme"

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

## 📈 Performance Monitoring

### Resource Usage
```bash
# Check process resource usage
ps aux | grep -E "(ragme|uvicorn|node)" | grep -v grep

# Check port usage
lsof -i :8020 -i :8021 -i :8022
```

### Memory and CPU
```bash
# Monitor system resources
top -p $(pgrep -f "ragme|uvicorn|node" | tr '\n' ',' | sed 's/,$//')
```

## 🔧 Configuration

### Environment Variables
The process management system respects these environment variables:
- `RAGME_API_URL`: API server URL (default: http://localhost:8021)
- `RAGME_MCP_URL`: MCP server URL (default: http://localhost:8022)
- `RAGME_API_PORT`: API server port (default: 8021)
- `RAGME_MCP_PORT`: MCP server port (default: 8022)
- `RAGME_FRONTEND_PORT`: Frontend port (default: 8020)
- `VECTOR_DB_TYPE`: Vector database type (default: milvus)

### PID File Management
The system uses a `.pid` file to track running processes:
- Created when services start
- Cleaned up when services stop
- Validated during status checks
- Used for graceful shutdowns

### Port Management
The system manages these ports (configurable via RAGME_*_PORT environment variables):
- **8020**: New frontend (default, configurable via `RAGME_FRONTEND_PORT`)
- **8020**: Legacy UI (optional)
- **8021**: API server (required, configurable via `RAGME_API_PORT`)
- **8022**: MCP server (required, configurable via `RAGME_MCP_PORT`)

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
- **New Frontend**: http://localhost:8020 (default)
- **Legacy UI**: http://localhost:8020
- **API Docs**: http://localhost:8021/docs
- **MCP Docs**: http://localhost:8022/docs 