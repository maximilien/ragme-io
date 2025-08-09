# Troubleshooting Guide

This guide covers common issues and their solutions for RAGme AI.

## 🚨 Common Issues

### Environment Variable Configuration Not Taking Effect

**Problem**: Changing `.env` files (APPLICATION_*, VECTOR_DB_TYPE, collection names) doesn't take effect after restart.

**Symptoms**:
- Application still shows old name/title after switching `.env` files
- Still connecting to old vector database collection
- Environment changes appear ignored

**Solution**: ✅ **FIXED!** This was a critical bug that has been resolved. The system now properly reads and applies all environment variable changes:

1. **Verify configuration loading**:
   ```bash
   ./tools/config-validator.sh
   ```

2. **Check environment variables are loaded**:
   ```bash
   python3 -c "
   from src.ragme.utils.config_manager import config
   print(f'App name: {config.get(\"application.name\")}')
   print(f'DB type: {config.get(\"vector_databases.default\")}')
   "
   ```

3. **Proper environment switching**:
   ```bash
   ./stop.sh
   cp .env.app.viewfinder-ai .env  # or your desired environment
   ./start.sh
   ```

**What was fixed**:
- Environment variable syntax in config.yaml (changed from `{$VAR}` to `${VAR}`)
- Dynamic VECTOR_DB_TYPE selection and mapping
- Proper configuration loading and substitution

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

**Problem**: New frontend (default port 3020) is not accessible.

**Symptoms**:
```
Cannot connect to http://localhost:3020
```

**Note**: The frontend port can be customized using the `RAGME_FRONTEND_PORT` environment variable.

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

### API Server Not Responding

**Problem**: API server (default port 8021) is not responding to requests.

**Symptoms**:
```
Connection refused on port 8021
```

**Note**: The API port can be customized using the `RAGME_API_PORT` environment variable.

**Solution**:
1. **Check API server status**:
   ```bash
   ./stop.sh status
   ```
2. **Restart API server**:
   ```bash
   ./stop.sh restart
   ```
3. **Check API logs**:
   ```bash
   ./tools/tail-logs.sh api
   ```
4. **Test API endpoint**:
   ```bash
   curl --max-time 10 http://localhost:8021/docs
   ```

### MCP Server Issues

**Problem**: MCP server (default port 8022) is not processing documents.

**Note**: The MCP port can be customized using the `RAGME_MCP_PORT` environment variable.

**Symptoms**:
```
MCP server not responding
Document processing failures
```

**Solution**:
1. **Check MCP server status**:
   ```bash
   ./stop.sh status
   ```
2. **Restart MCP server**:
   ```bash
   ./stop.sh restart
   ```
3. **Check MCP logs**:
   ```bash
   ./tools/tail-logs.sh mcp
   ```
4. **Test MCP endpoint**:
   ```bash
   curl --max-time 10 http://localhost:8022/docs
   ```

### File Monitoring Not Working

**Problem**: Files placed in `watch_directory/` are not being processed.

**Symptoms**:
```
New files not detected
No automatic processing
```

**Solution**:
1. **Check if file monitor is running**:
   ```bash
   ./stop.sh status
   ```
2. **Restart file monitor**:
   ```bash
   ./stop.sh restart
   ```
3. **Check agent logs**:
   ```bash
   ./tools/tail-logs.sh agent
   ```
4. **Verify file permissions**:
   ```bash
   ls -la watch_directory/
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

## 🔍 Debugging

For comprehensive debugging information, see [Process Management Guide](PROCESS_MANAGEMENT.md).

### Quick Debugging Steps

1. **Check service status**:
   ```bash
   ./stop.sh status
   ```

2. **Monitor logs in real-time**:
   ```bash
   ./tools/tail-logs.sh all
   ```

3. **Test individual components**:
   ```bash
   curl --max-time 10 http://localhost:8021/docs  # API
   curl --max-time 10 http://localhost:8022/docs  # MCP
   open http://localhost:3020                     # Frontend
   ```

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

For detailed process management and emergency procedures, see [Process Management Guide](PROCESS_MANAGEMENT.md). 