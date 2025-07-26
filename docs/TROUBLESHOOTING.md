# Troubleshooting Guide

This guide covers common issues and their solutions for RAGme AI.

## 🚨 Common Issues

### Weaviate Connection Errors

**Problem**: `WeaviateGRPCUnavailableError` or connection timeouts when starting services.

**Symptoms**:
```
weaviate.exceptions.WeaviateGRPCUnavailableError: 
Weaviate v1.31.5 makes use of a high-speed gRPC API as well as a REST API.
Unfortunately, the gRPC health check against Weaviate could not be completed.
```

**Solution**: 
1. **For local development**: The system now defaults to Milvus, which doesn't require external services
2. **For Weaviate Cloud**: Ensure your credentials are properly configured in `.env`:
   ```bash
   VECTOR_DB_TYPE=weaviate
   WEAVIATE_API_KEY=your-api-key
   WEAVIATE_URL=https://your-cluster.weaviate.network
   ```

**Automatic Fallback**: If Weaviate connection fails, the system automatically falls back to Milvus for local development.

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
   # For local development (default)
   VECTOR_DB_TYPE=milvus
   
   # For OpenAI queries
   OPENAI_API_KEY=your-openai-key
   
   # For Weaviate Cloud (optional)
   VECTOR_DB_TYPE=weaviate
   WEAVIATE_API_KEY=your-weaviate-key
   WEAVIATE_URL=https://your-cluster.weaviate.network
   ```

### Port Conflicts

**Problem**: Services fail to start because ports are already in use.

**Solution**:
1. Check what's using the ports:
   ```bash
   lsof -i :8020  # UI
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

### Test Individual Components

```bash
# Test API
curl http://localhost:8021/docs

# Test MCP
curl http://localhost:8022/docs

# Test UI
open http://localhost:8020
```

## 🚀 Performance Issues

### Slow Startup

**Problem**: Services take a long time to start.

**Causes**:
- Large vector database
- Network connectivity issues
- Resource constraints

**Solutions**:
1. Use local Milvus instead of cloud Weaviate
2. Check network connectivity
3. Monitor system resources

### Memory Usage

**Problem**: High memory usage during operation.

**Solutions**:
1. Monitor with `./stop.sh status`
2. Restart services periodically
3. Consider using smaller vector dimensions

## 📞 Getting Help

If you encounter issues not covered here:

1. **Check the logs** in the terminal where services are running
2. **Verify configuration** in your `.env` file
3. **Try a clean restart**: `./stop.sh restart`
4. **Check system resources**: CPU, memory, disk space
5. **Review the [Process Management Guide](PROCESS_MANAGEMENT.md)**

## 🔄 Recent Fixes

### v1.1.0 Improvements

- ✅ **Automatic fallback to Milvus** when Weaviate connection fails
- ✅ **ResourceWarning suppression** for cleaner output
- ✅ **Better error handling** in vector database connections
- ✅ **Improved timeout configuration** for Weaviate connections
- ✅ **Enhanced process management** with status and restart commands
- ✅ **Default local development setup** with Milvus

These improvements make the system more robust and easier to use for local development. 