# Storage Service Documentation

## Overview

RAGme.io includes a comprehensive S3-compatible file storage service that provides persistent storage for documents and images. The storage service supports multiple backends and is designed for both local development and production deployments.

## Architecture

The storage service uses a clean abstraction layer that supports multiple storage backends:

- **MinIO**: Local development and testing
- **AWS S3**: Production deployments
- **Local Filesystem**: Simple file-based storage

### Service Independence

**Important**: MinIO runs as an independent service. RAGme never modifies MinIO source code - it only interacts with MinIO through its S3-compatible API.

## Configuration

### Storage Configuration in config.yaml

```yaml
# Storage Configuration
storage:
  type: "minio"  # Options: minio, s3, local
  minio:
    endpoint: "localhost:9000"
    access_key: "minioadmin"
    secret_key: "minioadmin"
    secure: false  # Set to true for HTTPS
    bucket_name: "ragme-storage"
    region: "us-east-1"
  s3:
    endpoint: "${S3_ENDPOINT}"
    access_key: "${S3_ACCESS_KEY}"
    secret_key: "${S3_SECRET_KEY}"
    bucket_name: "${S3_BUCKET_NAME}"
    region: "${S3_REGION:-us-east-1}"
    secure: true
  local:
    path: "${MINIO_LOCAL_PATH:-minio_data/}"
```

### Environment Variables

For S3 production deployments, set these environment variables:

```bash
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=your_bucket_name
S3_REGION=us-east-1
MINIO_LOCAL_PATH=./minio_data/
```

## Local Development with MinIO

### Automatic Setup

MinIO is automatically installed and configured during the setup process:

```bash
# Run the setup script (includes MinIO installation)
./setup.sh

# Start all services including MinIO
./start.sh
```

### Manual MinIO Management

```bash
# Start MinIO service only
./start.sh minio

# Stop MinIO service only
./stop.sh minio

# Check MinIO status
./stop.sh status
```

### MinIO Console

- **URL**: http://localhost:9001
- **Default Credentials**: minioadmin / minioadmin
- **Default Bucket**: ragme-storage

### MinIO Data Directory

MinIO stores its data in the `./minio_data/` directory, which is:
- Created automatically during setup
- Added to `.gitignore` to prevent data from being committed
- Configurable via the `MINIO_LOCAL_PATH` environment variable

## StorageService API

The `StorageService` class provides a comprehensive interface for file operations:

### Initialization

```python
from src.ragme.utils.storage import StorageService
from src.ragme.utils.config_manager import ConfigManager

# Initialize with default configuration
storage = StorageService()

# Initialize with custom configuration
config = ConfigManager()
storage = StorageService(config)
```

### File Operations

#### Upload Files

```python
# Upload from file path
object_name = storage.upload_file(
    file_path="/path/to/document.pdf",
    object_name="documents/document.pdf",
    content_type="application/pdf"
)

# Upload binary data
object_name = storage.upload_data(
    data=b"file content",
    object_name="documents/file.txt",
    content_type="text/plain"
)
```

#### Download Files

```python
# Download to file path
success = storage.download_file(
    object_name="documents/document.pdf",
    file_path="/local/path/document.pdf"
)

# Get file data as bytes
file_data = storage.get_file("documents/document.pdf")
```

#### List Files

```python
# List all files
files = storage.list_files()

# List files with prefix
documents = storage.list_files(prefix="documents/")

# List files non-recursively
folders = storage.list_files(prefix="", recursive=False)
```

#### Delete Files

```python
# Delete a file
success = storage.delete_file("documents/document.pdf")
```

#### File Information

```python
# Check if file exists
exists = storage.file_exists("documents/document.pdf")

# Get file metadata
info = storage.get_file_info("documents/document.pdf")
# Returns: {'name': 'documents/document.pdf', 'size': 1024, 'last_modified': datetime, 'etag': 'abc123', 'content_type': 'application/pdf'}

# Generate presigned URL (temporary access)
url = storage.get_file_url("documents/document.pdf", expires_in=3600)
```

## Testing

### Unit Tests

Unit tests use mocked storage clients to test the StorageService interface:

```bash
# Run storage unit tests
uv run pytest tests/test_storage.py -v
```

### Integration Tests

Integration tests use a live MinIO server to test end-to-end functionality:

```bash
# Start MinIO for testing
./start.sh minio

# Run storage integration tests
uv run pytest tests/integration/test_storage_integration.py -v

# Stop MinIO
./stop.sh minio
```

### Test Coverage

The test suite covers:
- File upload/download operations
- Data upload/download operations
- File listing with prefixes
- File deletion and existence checks
- Presigned URL generation
- Error handling for non-existent files
- Cleanup after test failures
- Multiple file type support (PDF, images, binary data)

## Production Deployment

### AWS S3 Configuration

For production deployments, configure S3 storage:

1. **Create S3 Bucket**: Create a bucket in your AWS account
2. **Configure IAM**: Create an IAM user with S3 access permissions
3. **Update Configuration**: Set storage type to "s3" in config.yaml
4. **Set Environment Variables**: Configure S3 credentials and bucket information

### Security Considerations

- **Access Keys**: Store S3 access keys securely (use environment variables)
- **Bucket Permissions**: Configure appropriate bucket permissions
- **HTTPS**: Always use HTTPS for production S3 endpoints
- **CORS**: Configure CORS if accessing files from web browsers

### Monitoring

Monitor storage service logs:

```bash
# Monitor MinIO logs
./tools/tail-logs.sh minio

# Monitor API logs (includes storage operations)
./tools/tail-logs.sh api
```

## Troubleshooting

### Common Issues

#### MinIO Not Starting

```bash
# Check if port 9000 is available
lsof -i :9000

# Check MinIO logs
tail -f logs/minio.log

# Restart MinIO
./stop.sh minio
./start.sh minio
```

#### Permission Issues

```bash
# Check minio_data directory permissions
ls -la minio_data/

# Fix permissions if needed
chmod 755 minio_data/
```

#### Bucket Creation Issues

- Ensure MinIO is running before creating buckets
- Check MinIO console for bucket status
- Verify access key and secret key configuration

#### S3 Connection Issues

- Verify S3 endpoint URL
- Check access key and secret key
- Ensure bucket exists and is accessible
- Verify region configuration

### Log Analysis

Storage service logs include:
- File operation details
- Error messages and stack traces
- Performance metrics
- Authentication and authorization events

## Performance Considerations

### Local Development

- MinIO provides good performance for local development
- File operations are typically fast for small to medium files
- Consider file size limits for large uploads

### Production S3

- S3 provides excellent scalability and reliability
- Use appropriate S3 storage classes for cost optimization
- Consider CDN integration for frequently accessed files
- Monitor S3 costs and usage patterns

## Future Enhancements

Potential improvements to the storage service:

- **File Versioning**: Support for file versioning and rollback
- **Compression**: Automatic file compression for storage optimization
- **Encryption**: Client-side encryption for sensitive files
- **Caching**: Local caching for frequently accessed files
- **Backup**: Automated backup and recovery procedures
- **Analytics**: File access analytics and usage reporting
