# RAGme Kubernetes Manifests Guide

This guide explains the Kubernetes manifests and deployment patterns used for RAGme.

## 📋 Manifest Overview

The Kubernetes deployment consists of several manifest files organized for modularity and maintainability.

### Core Manifests

| File | Purpose | Resources |
|------|---------|-----------|
| `namespace.yaml` | RAGme namespace | Namespace |
| `configmap.yaml` | Configuration and secrets | ConfigMap, Secret |
| `shared-storage.yaml` | Persistent volumes | PersistentVolumeClaim |
| `*-deployment.yaml` | Service deployments | Deployment, Service |
| `kustomization.yaml` | Kustomize configuration | Kustomization |

## 🏗️ Resource Architecture

### Namespace Structure

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ragme
  labels:
    app: ragme
    version: v1
```

All RAGme resources are deployed in the `ragme` namespace for isolation and organization.

### Configuration Management

#### ConfigMap

Non-sensitive configuration is stored in ConfigMaps:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ragme-config
  namespace: ragme
data:
  RAGME_API_PORT: "8021"
  RAGME_MCP_PORT: "8022"
  RAGME_FRONTEND_PORT: "8020"
  RAGME_API_URL: "http://ragme-api:8021"
  RAGME_MCP_URL: "http://ragme-mcp:8022"
  VECTOR_DB_TYPE: "milvus"
  MINIO_ENDPOINT: "ragme-minio:9000"
```

#### Secrets

Sensitive data is stored in Kubernetes Secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ragme-secrets
  namespace: ragme
type: Opaque
stringData:
  OPENAI_API_KEY: "your-openai-api-key-here"
  WEAVIATE_API_KEY: "your-weaviate-api-key"
  MINIO_ACCESS_KEY: "minioadmin"
  MINIO_SECRET_KEY: "minioadmin"
```

### Storage Architecture

#### Shared Storage

All RAGme services share a common volume for file processing:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ragme-shared-pvc
  namespace: ragme
spec:
  accessModes:
  - ReadWriteMany  # Shared across multiple pods
  resources:
    requests:
      storage: 5Gi
```

#### Service-Specific Storage

Each stateful service has dedicated storage:

- **MinIO**: 10Gi ReadWriteOnce for object storage
- **Weaviate**: 2Gi ReadWriteOnce for vector database

## 🚀 Service Deployments

### API Service

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ragme-api
  namespace: ragme
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ragme
      component: api
  template:
    spec:
      containers:
      - name: api
        image: ragme-api:latest
        ports:
        - containerPort: 8021
        env:
        - name: RAGME_API_PORT
          valueFrom:
            configMapKeyRef:
              name: ragme-config
              key: RAGME_API_PORT
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ragme-secrets
              key: OPENAI_API_KEY
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        - name: watch-directory
          mountPath: /app/watch_directory
        livenessProbe:
          httpGet:
            path: /health
            port: 8021
        readinessProbe:
          httpGet:
            path: /ready
            port: 8021
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Service Definitions

Each service has both ClusterIP and NodePort services:

```yaml
# Internal service for cluster communication
apiVersion: v1
kind: Service
metadata:
  name: ragme-api
  namespace: ragme
spec:
  selector:
    app: ragme
    component: api
  ports:
  - name: http
    port: 8021
    targetPort: 8021
  type: ClusterIP

---
# External access via NodePort
apiVersion: v1
kind: Service
metadata:
  name: ragme-api-nodeport
  namespace: ragme
spec:
  selector:
    app: ragme
    component: api
  ports:
  - name: http
    port: 8021
    targetPort: 8021
    nodePort: 30021
  type: NodePort
```

## 🌐 Network Configuration

### Internal Communication

Services communicate using Kubernetes DNS:

- `ragme-api:8021` - API service
- `ragme-mcp:8022` - MCP service  
- `ragme-minio:9000` - MinIO service
- `ragme-weaviate:8080` - Weaviate service

### External Access

#### NodePort Services

| Service | NodePort | Internal Port | URL |
|---------|----------|---------------|-----|
| Frontend | 30020 | 8020 | http://localhost:30020 |
| API | 30021 | 8021 | http://localhost:30021 |
| MCP | 30022 | 8022 | http://localhost:30022 |
| MinIO API | 30900 | 9000 | http://localhost:30900 |
| MinIO Console | 30901 | 9001 | http://localhost:30901 |
| Weaviate | 30080 | 8080 | http://localhost:30080 |

#### Ingress (Optional)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ragme-frontend-ingress
  namespace: ragme
spec:
  rules:
  - host: ragme.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ragme-frontend
            port:
              number: 8020
```

## 🛡️ Security Considerations

### Container Security

1. **Non-root execution:**
   ```dockerfile
   # Use non-root user
   RUN adduser --disabled-password --gecos '' ragme
   USER ragme
   ```

2. **Minimal attack surface:**
   ```dockerfile
   # Use slim base images
   FROM python:3.11-slim
   
   # Remove unnecessary packages
   RUN apt-get clean && rm -rf /var/lib/apt/lists/*
   ```

3. **Security context:**
   ```yaml
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     fsGroup: 1000
     capabilities:
       drop:
       - ALL
   ```

### Network Security

1. **Network policies:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: ragme-network-policy
   spec:
     podSelector:
       matchLabels:
         app: ragme
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: ragme
   ```

2. **Service mesh integration:**
   - Istio sidecar injection
   - mTLS between services
   - Traffic policies

## 📊 Resource Management

### Resource Requirements

Default resource allocations:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi" 
    cpu: "1000m"
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ragme-api-hpa
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

### Vertical Pod Autoscaling

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ragme-api-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ragme-api
  updatePolicy:
    updateMode: "Auto"
```

## 🔧 Deployment Strategies

### Rolling Updates

Default deployment strategy for zero-downtime updates:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 25%
      maxSurge: 25%
```

### Blue-Green Deployment

For critical updates with instant rollback:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 100%
```

### Canary Deployment

Using Argo Rollouts or Flagger for gradual rollouts:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: ragme-api-rollout
spec:
  replicas: 5
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {}
      - setWeight: 40
      - pause: {duration: 10}
      - setWeight: 60
      - pause: {duration: 10}
      - setWeight: 80
      - pause: {duration: 10}
```

## 🔍 Monitoring and Observability

### Health Endpoints

All services expose health endpoints:

- `/health` - Liveness probe endpoint
- `/ready` - Readiness probe endpoint  
- `/metrics` - Prometheus metrics (if enabled)

### Logging

Structured logging to stdout for collection by Kubernetes:

```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
```

### Metrics Collection

Prometheus metrics integration:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ragme-api-metrics
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8021"
    prometheus.io/path: "/metrics"
spec:
  ports:
  - name: metrics
    port: 8021
    targetPort: 8021
```

## 🔄 GitOps Integration

### ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ragme
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/maximilien/ragme-io
    targetRevision: HEAD
    path: deployment/k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: ragme
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Flux Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: ragme
  namespace: flux-system
spec:
  interval: 5m
  path: "./deployment/k8s"
  prune: true
  sourceRef:
    kind: GitRepository
    name: ragme-repo
```

## 🧪 Testing

### Manifest Validation

```bash
# Validate manifests
kubectl apply --dry-run=client -k deployment/k8s/

# Kubeval validation
kubeval deployment/k8s/*.yaml

# OPA Gatekeeper policies
kubectl apply -f policies/security-policy.yaml
```

### Load Testing

```bash
# Deploy test load
kubectl apply -f deployment/tests/load-test.yaml

# Monitor performance
kubectl top pods -n ragme --containers
```