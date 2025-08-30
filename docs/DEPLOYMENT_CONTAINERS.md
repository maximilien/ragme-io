# RAGme Containerization Guide

This guide covers containerization of RAGme services for Kubernetes deployment.

## 🐳 Container Architecture

RAGme consists of multiple microservices that are containerized separately:

### Service Containers

| Service | Container | Base Image | Purpose |
|---------|-----------|------------|---------|
| **API** | `ragme-api` | `python:3.11-slim` | REST API and core RAG functionality |
| **MCP** | `ragme-mcp` | `python:3.11-slim` | Document processing service |
| **Agent** | `ragme-agent` | `python:3.11-slim` | File monitoring and ingestion |
| **Frontend** | `ragme-frontend` | `node:18-slim` | Web interface and UI |

### External Services

| Service | Container | Purpose |
|---------|-----------|---------|
| **MinIO** | `minio/minio:latest` | Object storage service |
| **Weaviate** | `cr.weaviate.io/semitechnologies/weaviate:1.25.0` | Vector database |

## 🏗️ Dockerfile Details

### Python Services (API, MCP, Agent)

All Python services share a similar containerization pattern:

```dockerfile
FROM python:3.11-slim

# System dependencies for RAGme
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libmagic1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies with uv
RUN pip install uv
COPY requirements.txt pyproject.toml ./
RUN uv pip install --system -r requirements.txt

# Application code
COPY src/ src/
COPY config.yaml.example config.yaml

# Runtime configuration
EXPOSE 8021
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8021/health || exit 1

CMD ["uvicorn", "src.ragme.apis.api:app", "--host", "0.0.0.0", "--port", "8021"]
```

### Frontend Service

The frontend uses Node.js with TypeScript compilation:

```dockerfile
FROM node:18-slim

# Application setup
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --only=production

# Build process
COPY frontend/ .
RUN npm run build

# Runtime
EXPOSE 8020
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

CMD ["npm", "start"]
```

## 🔧 Build Process

### Manual Building

```bash
# Build all containers
cd deployment/scripts
./build-containers.sh

# Build individual services
podman build -f deployment/containers/Dockerfile.api -t ragme-api:latest .
podman build -f deployment/containers/Dockerfile.mcp -t ragme-mcp:latest .
podman build -f deployment/containers/Dockerfile.agent -t ragme-agent:latest .
podman build -f deployment/containers/Dockerfile.frontend -t ragme-frontend:latest .
```

### Automated Building

The deployment script handles building automatically:

```bash
cd deployment
./deploy.sh build  # Build images only
./deploy.sh        # Build and deploy
```

## 📦 Container Registry

### Local Development

For local development, images are loaded directly into Kind:

```bash
# Local registry for Kind
podman run -d --name kind-registry -p 5001:5000 registry:2

# Tag and push images
podman tag ragme-api:latest localhost:5001/ragme-api:latest
podman push localhost:5001/ragme-api:latest
```

### Production Deployment

For production, push to your container registry:

```bash
# Configure registry
export REGISTRY="docker.io/myorg"
export TAG="v1.0.0"

# Push images
./deployment/scripts/push-containers.sh $REGISTRY $TAG
```

## 🌐 Environment Configuration

### Container Environment Variables

Each container accepts these environment variables:

#### Common Variables
- `OPENAI_API_KEY` - Required for AI functionality
- `VECTOR_DB_TYPE` - Vector database type (weaviate, milvus)
- `MINIO_ENDPOINT` - MinIO service endpoint
- `RAGME_API_URL` - API service URL
- `RAGME_MCP_URL` - MCP service URL

#### Service-Specific Variables

**API Service:**
- `RAGME_API_PORT=8021`
- `VECTOR_DB_TEXT_COLLECTION_NAME`
- `VECTOR_DB_IMAGE_COLLECTION_NAME`

**MCP Service:**
- `RAGME_MCP_PORT=8022`

**Agent Service:**
- `WATCH_DIRECTORY=/app/watch_directory`

**Frontend Service:**
- `RAGME_FRONTEND_PORT=8020`
- `NODE_ENV=production`

### Configuration Management

Configuration is managed through:

1. **ConfigMaps** - Non-sensitive configuration
2. **Secrets** - API keys and sensitive data
3. **Environment variables** - Runtime configuration

## 💾 Storage

### Volume Mounts

| Service | Mount Point | Type | Purpose |
|---------|-------------|------|---------|
| All Services | `/app/logs` | `emptyDir` | Application logs |
| API/MCP/Agent | `/app/watch_directory` | `PVC` | Shared file processing |
| MinIO | `/data` | `PVC` | Object storage data |
| Weaviate | `/var/lib/weaviate` | `PVC` | Vector database data |

### Persistent Volumes

- **Shared PVC** (`ragme-shared-pvc`) - 5Gi ReadWriteMany for file sharing
- **MinIO PVC** (`ragme-minio-pvc`) - 10Gi ReadWriteOnce for object storage
- **Vector DB PVC** (`ragme-vector-db-pvc`) - 2Gi ReadWriteOnce for vector data

## 🔍 Health Checks

### HTTP Health Checks

Services with HTTP endpoints include health checks:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8021/health || exit 1
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8021
  initialDelaySeconds: 30
  periodSeconds: 20

readinessProbe:
  httpGet:
    path: /ready
    port: 8021
  initialDelaySeconds: 5
  periodSeconds: 5
```

## 🐛 Debugging

### Container Debugging

```bash
# Run container interactively
podman run -it --rm ragme-api:latest /bin/bash

# Check container logs
podman logs <container-id>

# Inspect container
podman inspect ragme-api:latest
```

### Kubernetes Debugging

```bash
# Pod logs
kubectl logs -f deployment/ragme-api -n ragme

# Execute into pod
kubectl exec -it deployment/ragme-api -n ragme -- /bin/bash

# Describe resources
kubectl describe pod <pod-name> -n ragme
kubectl describe service ragme-api -n ragme
```

## 🔒 Security

### Container Security

- Non-root user execution
- Minimal base images (slim/distroless)
- Security context restrictions
- Resource limits

### Kubernetes Security

- RBAC for operator permissions
- Network policies for service isolation
- Secret management for sensitive data
- Security contexts for pods

## 📈 Monitoring

### Resource Monitoring

```bash
# Check resource usage
kubectl top pods -n ragme
kubectl top nodes

# Monitor events
kubectl get events -n ragme --watch
```

### Application Monitoring

- Health check endpoints: `/health`, `/ready`
- Metrics collection (if enabled)
- Log aggregation from all services

## 🚀 Scaling

### Manual Scaling

```bash
# Scale API replicas
kubectl scale deployment ragme-api --replicas=3 -n ragme

# Scale using operator
kubectl patch ragme ragme-sample -n ragme --type='merge' -p='{"spec":{"replicas":{"api":3}}}'
```

### Auto-scaling

Configure Horizontal Pod Autoscaler:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ragme-api-hpa
  namespace: ragme
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ragme-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```