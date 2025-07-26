# Troubleshooting Guide

This guide covers common issues and their solutions for RAGme AI.

## �� Common Issues

### Vector Database Connection Errors

**Problem**: Connection errors when starting services.

**Symptoms**:
```
ConnectionError: Failed to connect to vector database
```

**Solution**: 
1. **For local development**: The system now defaults to Milvus Lite, which doesn't require external services
2. **For Weaviate Cloud**: Ensure your credentials are properly configured in `.env`:
   ```bash
   VECTOR_DB_TYPE=weaviate
   WEAVIATE_API_KEY=your-api-key
   WEAVIATE_URL=https://your-cluster.weaviate.network
   ```
3. **For local Weaviate**: Ensure local Weaviate is running:
   ```bash
   ./tools/weaviate-local.sh status
   ./tools/weaviate-local.sh start
   ```

**Automatic Fallback**: If vector database connection fails, the system will show helpful error messages and guide you to the correct configuration.

### Frontend Not Loading

**Problem**: New frontend (port 3020) is not accessible.

**Symptoms**:
```
Cannot connect to http://localhost:3020
```

**Solution**:
1. **Check if frontend is running**:
   ```bash
   ./stop.sh status
   ```
2. **Restart frontend only**:
   ```bash
   ./start.sh restart-frontend
   ```
3. **Check frontend logs**:
   ```bash
   ./tools/tail-logs.sh frontend
   ```
4. **Rebuild frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   npm start
   ```

### Legacy UI Not Loading

**Problem**: Legacy Streamlit UI (port 8020) is not accessible.

**Symptoms**:
```
Cannot connect to http://localhost:8020
```

**Solution**:
1. **Start with legacy UI**:
   ```bash
   ./start.sh legacy-ui
   ```
2. **Check legacy UI logs**:
   ```bash
   ./tools/tail-logs.sh legacy-ui
   ```
3. **Check if port is in use**:
   ```bash
   lsof -i :8020
   ```

### ResourceWarning: unclosed file

**Problem**: `ResourceWarning: unclosed file <_io.TextIOWrapper name=0 mode='r' encoding='UTF-8'>`

**Solution**: This warning has been suppressed in the codebase. The warning was caused by temporary file handles in the MCP server, which are now properly managed.

### Milvus Deprecation Warnings

**Problem**: Deprecation warnings from pkg_resources in Milvus Lite.

**Symptoms**:
```
DeprecationWarning: pkg_resources is deprecated as an API
```

**Solution**: This is a known issue with Milvus Lite dependencies. The warning is harmless and doesn't affect functionality. It will be resolved in future versions of Milvus Lite.

## 🔧 Configuration Issues

### Missing Environment Variables

**Problem**: Services fail to start due to missing configuration.

**Solution**: 
1. Copy the example configuration:
   ```bash
   cp env.example .env
   ```
2. Edit `.env` with your settings:
   ```bash
   # For local development (default - recommended)
   VECTOR_DB_TYPE=milvus
   
   # For OpenAI queries
   OPENAI_API_KEY=your-openai-key
   
   # For Weaviate Cloud (optional)
   VECTOR_DB_TYPE=weaviate
   WEAVIATE_API_KEY=your-weaviate-key
   WEAVIATE_URL=https://your-cluster.weaviate.network
   
   # For local Weaviate (optional)
   VECTOR_DB_TYPE=weaviate-local
   WEAVIATE_LOCAL_URL=http://localhost:8080
   ```

### Port Conflicts

**Problem**: Services fail to start because ports are already in use.

**Solution**:
1. Check what's using the ports:
   ```bash
   lsof -i :3020  # New Frontend
   lsof -i :8020  # Legacy UI
   lsof -i :8021  # API
   lsof -i :8022  # MCP
   ```
2. Stop conflicting processes or use the process management:
   ```bash
   ./stop.sh stop
   ./stop.sh restart
   ```

## 🛠️ Process Management Issues

### Stale PID Files

**Problem**: Services show as running but aren't actually responding.

**Solution**:
```bash
# Check status
./stop.sh status

# Clean restart
./stop.sh restart
```

### Services Not Starting

**Problem**: Some services fail to start during restart.

**Solution**:
1. Check the logs in the terminal where services were started
2. Verify configuration in `.env`
3. Try manual start to see specific errors:
   ```bash
   # Start API manually
   uv run uvicorn src.ragme.api:app --reload --host 0.0.0.0 --port 8021
   ```

### Frontend Build Issues

**Problem**: Frontend fails to build or start.

**Symptoms**:
```
npm ERR! Failed to build
```

**Solution**:
1. **Clear node_modules and reinstall**:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```
2. **Check Node.js version** (requires 18+):
   ```bash
   node --version
   ```
3. **Check for TypeScript errors**:
   ```bash
   cd frontend
   npm run build
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
./tools/tail-logs.sh agent
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

## 🚀 Performance Issues

### Slow Startup

**Problem**: Services take a long time to start.

**Causes**:
- Large vector database
- Network connectivity issues
- Resource constraints
- Frontend build process

**Solutions**:
1. Use local Milvus instead of cloud Weaviate
2. Check network connectivity
3. Monitor system resources
4. Pre-build frontend: `cd frontend && npm run build`

### Memory Usage

**Problem**: High memory usage during operation.

**Solutions**:
1. Monitor with `./stop.sh status`
2. Restart services periodically
3. Consider using smaller vector dimensions
4. Check for memory leaks in long-running processes

### Frontend Performance

**Problem**: Frontend is slow or unresponsive.

**Solutions**:
1. **Check browser console** for JavaScript errors
2. **Clear browser cache** and reload
3. **Check WebSocket connection** in browser dev tools
4. **Monitor frontend logs**: `./tools/tail-logs.sh frontend`
5. **Restart frontend**: `./start.sh restart-frontend`

## 📞 Getting Help

If you encounter issues not covered here:

1. **Check the logs** in the terminal where services are running
2. **Verify configuration** in your `.env` file
3. **Try a clean restart**: `./stop.sh restart`
4. **Check system resources**: CPU, memory, disk space
5. **Review the [Process Management Guide](PROCESS_MANAGEMENT.md)**
6. **Check service status**: `./stop.sh status`

## 🔄 Recent Fixes

### v1.2.0 Improvements

- ✅ **New frontend UI** with three-pane layout and real-time features
- ✅ **Enhanced process management** with comprehensive status checking
- ✅ **Milvus as default** for local development (no external dependencies)
- ✅ **Local Weaviate support** with Podman-based deployment
- ✅ **Improved debugging tools** with real-time log monitoring
- ✅ **Better error handling** in vector database connections
- ✅ **Frontend build optimization** with TypeScript and modern tooling
- ✅ **Service-specific management** for individual component control

### v1.1.0 Improvements

- ✅ **Automatic fallback to Milvus** when Weaviate connection fails
- ✅ **ResourceWarning suppression** for cleaner output
- ✅ **Better error handling** in vector database connections
- ✅ **Improved timeout configuration** for Weaviate connections
- ✅ **Enhanced process management** with status and restart commands
- ✅ **Default local development setup** with Milvus

These improvements make the system more robust and easier to use for local development.

## 🎯 Quick Fixes

### Common Solutions

| Problem | Quick Fix |
|---------|-----------|
| Frontend not loading | `./start.sh restart-frontend` |
| Legacy UI not loading | `./start.sh legacy-ui` |
| Services not starting | `./stop.sh restart` |
| Port conflicts | `./stop.sh stop && ./start.sh` |
| Vector DB errors | Check `.env` configuration |
| Build errors | `cd frontend && npm install && npm run build` |
| Memory issues | `./stop.sh restart` |
| Log monitoring | `./tools/tail-logs.sh all` |

### Emergency Procedures

```bash
# Force kill all processes
pkill -f "ragme"
pkill -f "streamlit"
pkill -f "uvicorn"
pkill -f "node"

# Complete reset
rm -f .pid
./stop.sh stop
./start.sh

# Frontend reset
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
cd ..
./start.sh restart-frontend
``` 