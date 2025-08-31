# RAGme Kubernetes Operator Guide

The RAGme Operator provides declarative management of RAGme deployments using Kubernetes Custom Resources.

## 🎯 Overview

The RAGme Operator simplifies deployment and management of RAGme services by:

- **Declarative configuration** - Define desired state in YAML
- **Automated lifecycle management** - Handles creation, updates, and scaling
- **Integration with Kubernetes** - Native Kubernetes resource management
- **Operational best practices** - Health checks, resource management, security

## 🏗️ Operator Architecture

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Custom Resource Definition (CRD)** | Defines RAGme resource schema | `config/crd/ragme.io_ragmes.yaml` |
| **Controller** | Reconciles desired vs actual state | `internal/controller/ragme_controller.go` |
| **Manager** | Operator runtime and webhook server | `cmd/main.go` |
| **RBAC** | Permissions for operator to manage resources | `config/rbac/` |

### Custom Resource Schema

```go
type RAGmeSpec struct {
    Version    string         `json:"version,omitempty"`
    Images     RAGmeImages    `json:"images,omitempty"`
    Replicas   RAGmeReplicas  `json:"replicas,omitempty"`
    Storage    RAGmeStorage   `json:"storage,omitempty"`
    VectorDB   RAGmeVectorDB  `json:"vectorDB,omitempty"`
    Resources  RAGmeResources `json:"resources,omitempty"`
    ExternalAccess RAGmeExternalAccess `json:"externalAccess,omitempty"`
}
```

## 🚀 Installation

### Install CRDs

```bash
cd deployment/operator
kubectl apply -f config/crd/ragme.io_ragmes.yaml
```

### Deploy Operator

```bash
# Install RBAC
kubectl apply -f config/rbac/

# Deploy operator
kubectl apply -f config/manager/manager.yaml
```

### Verify Installation

```bash
# Check operator pod
kubectl get pods -n ragme-operator-system

# Check CRD registration
kubectl get crd ragmes.ragme.io

# Check operator logs
kubectl logs deployment/ragme-operator-controller-manager -n ragme-operator-system
```

## 📝 Custom Resource Examples

### Basic RAGme Deployment

```yaml
apiVersion: ragme.io/v1
kind: RAGme
metadata:
  name: ragme-basic
  namespace: ragme
spec:
  version: "latest"
  
  images:
    registry: "localhost:5001"
    tag: "latest"
    pullPolicy: "IfNotPresent"
  
  replicas:
    api: 2
    mcp: 2
    agent: 1
    frontend: 2
  
  storage:
    minio:
      enabled: true
      storageSize: "10Gi"
    sharedVolume:
      size: "5Gi"
  
  vectorDB:
    type: "weaviate"
    weaviate:
      enabled: true
      storageSize: "2Gi"
```

### Production RAGme Deployment

```yaml
apiVersion: ragme.io/v1
kind: RAGme
metadata:
  name: ragme-production
  namespace: ragme-prod
spec:
  version: "v1.0.0"
  
  images:
    registry: "docker.io/myorg"
    tag: "v1.0.0"
    pullPolicy: "Always"
  
  replicas:
    api: 3
    mcp: 3
    agent: 1
    frontend: 3
  
  storage:
    minio:
      enabled: false  # Use external S3
    sharedVolume:
      size: "20Gi"
      storageClass: "fast-ssd"
  
  vectorDB:
    type: "weaviate"
    weaviate:
      enabled: false  # Use Weaviate Cloud
  
  resources:
    api:
      requests: { memory: "1Gi", cpu: "1000m" }
      limits: { memory: "2Gi", cpu: "2000m" }
    mcp:
      requests: { memory: "1Gi", cpu: "1000m" }
      limits: { memory: "2Gi", cpu: "2000m" }
    frontend:
      requests: { memory: "512Mi", cpu: "500m" }
      limits: { memory: "1Gi", cpu: "1000m" }
  
  externalAccess:
    type: "Ingress"
    ingress:
      enabled: true
      host: "ragme.example.com"
      tlsEnabled: true
      annotations:
        cert-manager.io/cluster-issuer: "letsencrypt-prod"
        nginx.ingress.kubernetes.io/ssl-redirect: "true"
```

### Development RAGme Deployment

```yaml
apiVersion: ragme.io/v1
kind: RAGme
metadata:
  name: ragme-dev
  namespace: ragme-dev
spec:
  version: "develop"
  
  images:
    registry: "localhost:5001"
    tag: "develop"
    pullPolicy: "Always"
  
  replicas:
    api: 1
    mcp: 1
    agent: 1
    frontend: 1
  
  storage:
    minio:
      enabled: true
      storageSize: "5Gi"
    sharedVolume:
      size: "2Gi"
  
  vectorDB:
    type: "milvus"
    milvus:
      enabled: true
  
  resources:
    api:
      requests: { memory: "256Mi", cpu: "250m" }
      limits: { memory: "512Mi", cpu: "500m" }
```

## 🔄 Operator Operations

### Deployment Management

```bash
# Create RAGme deployment
kubectl apply -f my-ragme.yaml

# Get RAGme status
kubectl get ragme -n ragme

# Describe RAGme resource
kubectl describe ragme my-ragme -n ragme

# Check operator events
kubectl get events -n ragme --field-selector involvedObject.kind=RAGme
```

### Scaling

```bash
# Scale API replicas
kubectl patch ragme my-ragme -n ragme --type='merge' -p='{"spec":{"replicas":{"api":5}}}'

# Scale multiple services
kubectl patch ragme my-ragme -n ragme --type='merge' -p='{"spec":{"replicas":{"api":3,"frontend":3}}}'
```

### Updates

```bash
# Update container images
kubectl patch ragme my-ragme -n ragme --type='merge' -p='{"spec":{"images":{"tag":"v1.1.0"}}}'

# Update resources
kubectl patch ragme my-ragme -n ragme --type='merge' -p='{"spec":{"resources":{"api":{"limits":{"memory":"2Gi"}}}}}'
```

### Deletion

```bash
# Delete RAGme deployment (keeps data)
kubectl delete ragme my-ragme -n ragme

# Delete everything including storage
kubectl delete namespace ragme
```

## 🔧 Operator Development

### Setup Development Environment

```bash
cd deployment/operator

# Install dependencies
go mod download

# Install controller-gen and other tools
go install sigs.k8s.io/controller-tools/cmd/controller-gen@latest
go install sigs.k8s.io/controller-runtime/tools/setup-envtest@latest
```

### Development Workflow

```bash
# Generate code and manifests
make generate
make manifests

# Run tests
make test

# Run operator locally (against cluster)
make run

# Build operator binary
make build
```

### Custom Resource Development

1. **Modify types** in `api/v1/ragme_types.go`
2. **Regenerate manifests:**
   ```bash
   make generate
   make manifests
   ```
3. **Update controller logic** in `internal/controller/ragme_controller.go`
4. **Test changes:**
   ```bash
   make test
   make run
   ```

### Building Operator Image

```bash
# Build operator container
make container-build IMG=ragme-operator:latest

# Push to registry
make container-push IMG=docker.io/myorg/ragme-operator:v1.0.0
```

## 📊 Monitoring and Debugging

### Operator Logs

```bash
# Follow operator logs
kubectl logs -f deployment/ragme-operator-controller-manager -n ragme-operator-system

# Get recent events
kubectl get events -n ragme-operator-system --sort-by='.lastTimestamp'
```

### RAGme Resource Status

```bash
# Check RAGme resource status
kubectl get ragme my-ragme -n ragme -o yaml

# Monitor reconciliation
kubectl describe ragme my-ragme -n ragme
```

### Debugging Failed Deployments

```bash
# Check pod status
kubectl get pods -n ragme

# Get pod logs
kubectl logs deployment/ragme-api -n ragme

# Check events
kubectl get events -n ragme --field-selector involvedObject.name=ragme-api

# Debug operator decisions
kubectl logs deployment/ragme-operator-controller-manager -n ragme-operator-system --tail=100
```

## 🧪 Testing

### Unit Tests

```bash
cd deployment/operator

# Run unit tests
go test ./internal/controller/... -short

# Run with coverage
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out
```

### Integration Tests

```bash
# Run controller integration tests
make test

# Test against real cluster
KUBECONFIG=~/.kube/config go test ./test/integration/... -timeout=10m
```

### End-to-End Testing

```bash
# Full deployment test
cd deployment
./deploy.sh

# Verify operator functionality
kubectl apply -f operator/config/samples/ragme_v1_ragme.yaml
kubectl wait --for=condition=ready ragme/ragme-sample -n ragme --timeout=300s
```

## 🔒 Security and RBAC

### Operator Permissions

The operator requires these permissions:

```yaml
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets", "services", "persistentvolumeclaims"]
  verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
- apiGroups: ["ragme.io"]
  resources: ["ragmes", "ragmes/status", "ragmes/finalizers"]
  verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
```

### Least Privilege Principle

The operator follows security best practices:

1. **Namespace isolation** - Operator runs in separate namespace
2. **Minimal permissions** - Only required RBAC rules
3. **Non-root execution** - Containers run as non-root user
4. **Secret management** - Sensitive data in Kubernetes Secrets

## 📈 Best Practices

### Resource Management

1. **Set resource limits** to prevent resource starvation
2. **Use requests** for scheduling optimization  
3. **Configure autoscaling** for dynamic workloads
4. **Monitor resource usage** and adjust accordingly

### High Availability

1. **Multiple replicas** for stateless services
2. **Pod anti-affinity** to distribute across nodes
3. **Persistent storage** for stateful components
4. **Health checks** for automatic recovery

### Configuration Management

1. **Use ConfigMaps** for non-sensitive configuration
2. **Use Secrets** for API keys and passwords
3. **Environment-specific overlays** with Kustomize
4. **Version configuration** with your application

### Deployment Patterns

1. **Rolling updates** for zero-downtime deployments
2. **Canary releases** for risk mitigation
3. **Blue-green deployment** for instant rollback
4. **GitOps workflows** for declarative management

## 🔮 Advanced Features

### Multi-tenancy

Deploy multiple RAGme instances:

```bash
# Deploy for different teams
kubectl apply -f ragme-team-a.yaml -n team-a
kubectl apply -f ragme-team-b.yaml -n team-b
```

### Cross-cluster Deployment

Deploy RAGme across multiple clusters:

```yaml
# Cluster A: Frontend and API
spec:
  replicas:
    frontend: 2
    api: 2
    mcp: 0
    agent: 0

# Cluster B: Processing services  
spec:
  replicas:
    frontend: 0
    api: 0
    mcp: 2
    agent: 1
```

### External Service Integration

Connect to external services:

```yaml
spec:
  storage:
    minio:
      enabled: false  # Use external S3
  vectorDB:
    type: "weaviate"
    weaviate:
      enabled: false  # Use Weaviate Cloud
      url: "https://my-cluster.weaviate.network"
```