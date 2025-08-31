# RAGme Deployment Troubleshooting Guide

This guide helps diagnose and resolve common issues with RAGme Kubernetes deployments.

## 🚨 Common Issues

### Container Build Issues

#### Problem: Podman not found
```bash
Error: podman is not installed. Please install podman first.
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y podman

# RHEL/CentOS/Fedora
sudo dnf install podman

# macOS
brew install podman
```

#### Problem: Container build fails
```bash
Error building image: missing requirements.txt
```

**Solution:**
```bash
# Ensure you're in project root
cd /path/to/ragme-io

# Verify files exist
ls requirements.txt pyproject.toml

# Check build context
./deployment/scripts/build-containers.sh
```

#### Problem: Out of disk space during build
```bash
Error: no space left on device
```

**Solution:**
```bash
# Clean up podman images and containers
podman system prune -af

# Remove unused images
podman image prune -af

# Check disk usage
df -h
```

### Kind Cluster Issues

#### Problem: Kind not installed
```bash
Error: kind is not installed
```

**Solution:**
```bash
# Linux
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# macOS
brew install kind

# Verify installation
kind --version
```

#### Problem: Cluster creation fails
```bash
Error: failed to create cluster: port 8080 already in use
```

**Solution:**
```bash
# Check what's using the port
lsof -i :8080
netstat -tulpn | grep 8080

# Kill the process or use different ports
sudo kill <process-id>

# Delete existing cluster
kind delete cluster --name ragme-cluster
```

#### Problem: Cannot connect to cluster
```bash
Error: connection refused
```

**Solution:**
```bash
# Check cluster status
kind get clusters
kubectl cluster-info --context kind-ragme-cluster

# Reset kubeconfig
kind export kubeconfig --name ragme-cluster

# Verify connectivity
kubectl get nodes
```

### Pod Startup Issues

#### Problem: ImagePullBackOff
```bash
NAME       READY   STATUS             RESTARTS   AGE
ragme-api  0/1     ImagePullBackOff   0          2m
```

**Solution:**
```bash
# Check image exists
podman images | grep ragme-api

# Load image into kind cluster
kind load docker-image ragme-api:latest --name ragme-cluster

# Check pod events
kubectl describe pod ragme-api-xxx -n ragme
```

#### Problem: CrashLoopBackOff
```bash
NAME       READY   STATUS             RESTARTS   AGE
ragme-api  0/1     CrashLoopBackOff   3          5m
```

**Solution:**
```bash
# Check pod logs
kubectl logs ragme-api-xxx -n ragme

# Check previous container logs
kubectl logs ragme-api-xxx -n ragme --previous

# Common issues:
# 1. Missing environment variables
# 2. Missing dependencies
# 3. Configuration errors
```

#### Problem: Pending pods
```bash
NAME       READY   STATUS    RESTARTS   AGE
ragme-api  0/1     Pending   0          5m
```

**Solution:**
```bash
# Check node resources
kubectl top nodes
kubectl describe nodes

# Check events
kubectl get events -n ragme --sort-by='.lastTimestamp'

# Check PVC status
kubectl get pvc -n ragme
kubectl describe pvc ragme-shared-pvc -n ragme
```

### Storage Issues

#### Problem: PVC stuck in Pending
```bash
NAME               STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
ragme-shared-pvc   Pending                                      standard       5m
```

**Solution:**
```bash
# Check storage class
kubectl get storageclass

# For kind clusters, use local-path
kubectl patch pvc ragme-shared-pvc -n ragme -p '{"spec":{"storageClassName":"standard"}}'

# Or create local storage class
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path
provisioner: rancher.io/local-path
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
EOF
```

#### Problem: Volume mount failures
```bash
Error: failed to mount volume: permission denied
```

**Solution:**
```bash
# Check volume permissions
kubectl exec -it ragme-api-xxx -n ragme -- ls -la /app/

# Fix with init container
apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: volume-permissions
    image: busybox
    command: ['sh', '-c', 'chown -R 1000:1000 /app/watch_directory']
    volumeMounts:
    - name: watch-directory
      mountPath: /app/watch_directory
```

### Service Communication Issues

#### Problem: Service not found
```bash
Error: dial tcp: lookup ragme-mcp on 10.96.0.10:53: no such host
```

**Solution:**
```bash
# Check service exists
kubectl get services -n ragme

# Check service endpoints
kubectl get endpoints -n ragme

# Check DNS resolution from pod
kubectl exec -it ragme-api-xxx -n ragme -- nslookup ragme-mcp
```

#### Problem: Connection refused
```bash
Error: dial tcp 10.96.157.73:8022: connect: connection refused
```

**Solution:**
```bash
# Check if target service is ready
kubectl get pods -n ragme -l component=mcp

# Check service port configuration
kubectl describe service ragme-mcp -n ragme

# Test connectivity from source pod
kubectl exec -it ragme-api-xxx -n ragme -- curl http://ragme-mcp:8022/health
```

### Operator Issues

#### Problem: Operator not reconciling
```bash
RAGme resource created but no pods appearing
```

**Solution:**
```bash
# Check operator logs
kubectl logs deployment/ragme-operator-controller-manager -n ragme-operator-system

# Check RBAC permissions
kubectl auth can-i create deployments --as=system:serviceaccount:ragme-operator-system:ragme-operator-controller-manager

# Check CRD installation
kubectl get crd ragmes.ragme.io
```

#### Problem: Operator crash
```bash
Error: failed to start manager: no matches for kind "RAGme"
```

**Solution:**
```bash
# Install CRDs first
kubectl apply -f deployment/operator/config/crd/

# Restart operator
kubectl rollout restart deployment/ragme-operator-controller-manager -n ragme-operator-system
```

### Configuration Issues

#### Problem: Missing API keys
```bash
Error: OpenAI API key not provided
```

**Solution:**
```bash
# Check secret exists
kubectl get secret ragme-secrets -n ragme

# Update secret
kubectl patch secret ragme-secrets -n ragme --type='merge' -p='{"stringData":{"OPENAI_API_KEY":"your-key-here"}}'

# Restart affected pods
kubectl rollout restart deployment/ragme-api -n ragme
```

#### Problem: Wrong configuration values
```bash
Error: invalid vector database type: weaviat
```

**Solution:**
```bash
# Check ConfigMap
kubectl get configmap ragme-config -n ragme -o yaml

# Update configuration
kubectl patch configmap ragme-config -n ragme --type='merge' -p='{"data":{"VECTOR_DB_TYPE":"weaviate"}}'

# Restart pods to pick up changes
kubectl rollout restart deployment/ragme-api -n ragme
```

## 🔍 Debugging Commands

### Essential Debugging Commands

```bash
# Check all resources in namespace
kubectl get all -n ragme

# Check resource status and events
kubectl describe <resource-type> <resource-name> -n ragme

# Get detailed pod information
kubectl get pods -n ragme -o wide

# Check pod logs (current and previous)
kubectl logs <pod-name> -n ragme
kubectl logs <pod-name> -n ragme --previous

# Execute into pod for debugging
kubectl exec -it <pod-name> -n ragme -- /bin/bash

# Check network connectivity
kubectl exec -it <pod-name> -n ragme -- wget -qO- http://ragme-mcp:8022/health

# Port forward for local testing
kubectl port-forward service/ragme-frontend 8020:8020 -n ragme
```

### Advanced Debugging

```bash
# Check resource consumption
kubectl top pods -n ragme
kubectl top nodes

# Analyze events across cluster
kubectl get events --all-namespaces --sort-by='.lastTimestamp'

# Check cluster DNS
kubectl exec -it <pod-name> -n ragme -- nslookup kubernetes.default.svc.cluster.local

# Validate YAML before applying
kubectl apply --dry-run=client -f my-ragme.yaml

# Check RBAC permissions
kubectl auth can-i list pods --as=system:serviceaccount:ragme:default -n ragme
```

## 📊 Performance Troubleshooting

### High Resource Usage

```bash
# Monitor resource usage
kubectl top pods -n ragme --containers

# Check resource limits
kubectl describe pod <pod-name> -n ragme

# Adjust resources
kubectl patch ragme my-ragme -n ragme --type='merge' -p='{"spec":{"resources":{"api":{"limits":{"memory":"2Gi"}}}}}'
```

### Slow Response Times

```bash
# Check service health
kubectl exec -it <pod-name> -n ragme -- curl -w "\n%{time_total}" http://ragme-api:8021/health

# Monitor network latency
kubectl exec -it <pod-name> -n ragme -- ping ragme-mcp

# Check for resource throttling
kubectl describe pod <pod-name> -n ragme | grep -i throttl
```

### Storage Performance

```bash
# Check PVC status
kubectl get pvc -n ragme

# Test storage performance
kubectl exec -it <pod-name> -n ragme -- dd if=/dev/zero of=/app/watch_directory/test bs=1M count=100

# Check storage class performance
kubectl describe storageclass standard
```

## 🛠️ Recovery Procedures

### Complete Deployment Reset

```bash
# Delete RAGme deployment
kubectl delete ragme --all -n ragme

# Delete namespace (removes all resources)
kubectl delete namespace ragme

# Recreate from scratch
./deployment/deploy.sh
```

### Selective Service Restart

```bash
# Restart specific service
kubectl rollout restart deployment/ragme-api -n ragme

# Scale down and up
kubectl scale deployment ragme-api --replicas=0 -n ragme
kubectl scale deployment ragme-api --replicas=2 -n ragme
```

### Data Recovery

```bash
# Backup persistent data
kubectl exec -it <minio-pod> -n ragme -- tar czf /tmp/backup.tar.gz /data

# Copy backup out of cluster
kubectl cp ragme/<minio-pod>:/tmp/backup.tar.gz ./minio-backup.tar.gz

# Restore data to new deployment
kubectl cp ./minio-backup.tar.gz ragme/<new-minio-pod>:/tmp/
kubectl exec -it <new-minio-pod> -n ragme -- tar xzf /tmp/backup.tar.gz -C /
```

## 📞 Getting Help

### Log Collection

```bash
# Collect all logs
mkdir -p debug-logs
kubectl logs deployment/ragme-api -n ragme > debug-logs/api.log
kubectl logs deployment/ragme-mcp -n ragme > debug-logs/mcp.log
kubectl logs deployment/ragme-agent -n ragme > debug-logs/agent.log
kubectl logs deployment/ragme-frontend -n ragme > debug-logs/frontend.log

# Collect events
kubectl get events -n ragme --sort-by='.lastTimestamp' > debug-logs/events.log

# Collect resource states
kubectl get all -n ragme -o yaml > debug-logs/resources.yaml
```

### Support Information

When seeking help, provide:

1. **Environment details:**
   - Kubernetes version: `kubectl version`
   - Cluster type: Kind, EKS, GKE, etc.
   - Node information: `kubectl get nodes -o wide`

2. **RAGme deployment info:**
   - RAGme resource: `kubectl get ragme -n ragme -o yaml`
   - Pod status: `kubectl get pods -n ragme -o wide`
   - Service status: `kubectl get services -n ragme`

3. **Error logs:**
   - Application logs from affected services
   - Operator logs if using the operator
   - Kubernetes events

4. **Configuration:**
   - ConfigMap contents (redacted)
   - Environment variables (redacted)
   - Custom resource definition

### Community Resources

- [RAGme GitHub Issues](https://github.com/maximilien/ragme-io/issues)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [Operator Framework Documentation](https://operatorframework.io/)

## 🔄 Known Issues

### Issue: Agent replica must be 1

**Problem:** File monitoring agent doesn't work with multiple replicas
**Solution:** Always set `agent: 1` in replica configuration

### Issue: Storage class not available

**Problem:** Default storage class not found in some clusters
**Solution:** Specify appropriate storage class for your environment

### Issue: NodePort conflicts

**Problem:** NodePort ranges might conflict with existing services
**Solution:** Use different NodePort ranges or LoadBalancer type

### Issue: Resource limits too low

**Problem:** Pods getting OOMKilled with default resource limits
**Solution:** Increase memory limits based on your workload

```yaml
resources:
  api:
    limits:
      memory: "2Gi"  # Increase from 1Gi
      cpu: "2000m"   # Increase from 1000m
```