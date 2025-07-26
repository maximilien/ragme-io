# Process Management

RAGme AI uses a comprehensive process management system to handle multiple services. The `./stop.sh` script has been enhanced to provide full process lifecycle management.

## 🚀 Quick Start

```bash
# Start all services
./start.sh

# Check status
./stop.sh status

# Restart all services
./stop.sh restart

# Stop all services
./stop.sh stop
```

## 📋 Available Commands

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

RAGme AI runs four main services:

| Service | Port | Description | URL |
|---------|------|-------------|-----|
| Streamlit UI | 8020 | Web interface | http://localhost:8020 |
| FastAPI | 8021 | REST API | http://localhost:8021 |
| MCP | 8022 | Model Context Protocol | http://localhost:8022 |
| Local Agent | - | File monitoring | Background process |

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
lsof -i :8020
lsof -i :8021
lsof -i :8022

# Kill conflicting processes
./stop.sh stop
```

## 📊 Status Output Examples

### All Services Running
```
=== RAGme Process Status ===

📄 PID File Status:
   PID file exists with the following processes:
   ✅ Process 12345 is running
   ✅ Process 12346 is running
   ✅ Process 12347 is running
   ✅ Process 12348 is running

🌐 Port Status:
   ✅ Streamlit UI (port 8020) - Running (PID: 12345)
   ✅ FastAPI (port 8021) - Running (PID: 12346)
   ✅ MCP (port 8022) - Running (PID: 12347)

🎉 All RAGme services are running!
   • UI: http://localhost:8020
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
   ✅ Streamlit UI (port 8020) - Running (PID: 12345)
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

## 🚨 Emergency Procedures

### Force Kill All Processes
```bash
# If normal stop doesn't work
pkill -f "ragme"
pkill -f "streamlit"
pkill -f "uvicorn"
```

### Reset Everything
```bash
# Complete reset
rm -f .pid
./stop.sh stop
./start.sh
``` 