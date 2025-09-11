#!/bin/bash
# Test script to verify ConfigMap generation works

# Navigate to the deployment directory
cd deployment/scripts/kind

# Source the .env file first
set -a
source ../../../.env
set +a

echo "Testing ConfigMap generation..."
echo "OPENAI_API_KEY loaded: ${OPENAI_API_KEY:0:20}..."

# Test the generate_configmap function by extracting it
generate_configmap() {
    local output_file="${1:-kind/k8s/configmap-generated.yaml}"
    echo "Generating Kubernetes configmap from .env file to $output_file..."
    
    # Check if .env file exists
    if [ ! -f "../../../.env" ]; then
        echo "ERROR: .env file not found in project root"
        return 1
    fi
    
    # Source the .env file
    set -a
    source ../../../.env
    set +a
    
    # Generate configmap with proper variable expansion using printf
    printf 'apiVersion: v1
kind: ConfigMap
metadata:
  name: ragme-config
  namespace: ragme
  labels:
    app: ragme
data:
  # RAGme Configuration
  RAGME_API_PORT: "8021"
  RAGME_MCP_PORT: "8022"
  RAGME_FRONTEND_PORT: "8020"
  
  # Service URLs (internal cluster access for frontend server)
  RAGME_API_URL: "http://ragme-api:8021"
  RAGME_MCP_URL: "http://ragme-mcp:8022"
  
  # Vector Database Configuration (force weaviate-local for Kind)
  VECTOR_DB_TYPE: "%s"
  VECTOR_DB_TEXT_COLLECTION_NAME: "%s"
  VECTOR_DB_IMAGE_COLLECTION_NAME: "%s"
  
  # MinIO Configuration
  MINIO_ENDPOINT: "ragme-minio:9000"
  
  # Application Configuration
  APPLICATION_NAME: "%s"
  APPLICATION_VERSION: "%s"
  APPLICATION_TITLE: "%s"
  APPLICATION_DESCRIPTION: "%s"
  
  # Watch Directory
  WATCH_DIRECTORY: "%s"
  MINIO_LOCAL_PATH: "%s"
  
  # OAuth Configuration - use internal service URLs for Kubernetes
  GOOGLE_OAUTH_REDIRECT_URI: "http://ragme-api:8021/auth/google/callback"
  GITHUB_OAUTH_REDIRECT_URI: "http://ragme-api:8021/auth/github/callback"
  APPLE_OAUTH_REDIRECT_URI: "http://ragme-api:8021/auth/apple/callback"
---
apiVersion: v1
kind: Secret
metadata:
  name: ragme-secrets
  namespace: ragme
  labels:
    app: ragme
type: Opaque
stringData:
  # Required secrets - update these values
  OPENAI_API_KEY: "%s"
  
  # Optional secrets for external services
  WEAVIATE_API_KEY: "%s"
  WEAVIATE_URL: "%s"
  MILVUS_URI: "%s"
  MILVUS_TOKEN: "%s"
  
  # MinIO credentials
  MINIO_ACCESS_KEY: "%s"
  MINIO_SECRET_KEY: "%s"
  
  # S3 credentials (if using S3 instead of MinIO)
  S3_ENDPOINT: "%s"
  S3_ACCESS_KEY: "%s"
  S3_SECRET_KEY: "%s"
  S3_BUCKET_NAME: "%s"
  S3_REGION: "%s"
  
  # OAuth secrets - use values from .env file
  GOOGLE_OAUTH_CLIENT_ID: "%s"
  GOOGLE_OAUTH_CLIENT_SECRET: "%s"
  GITHUB_OAUTH_CLIENT_ID: "%s"
  GITHUB_OAUTH_CLIENT_SECRET: "%s"
  APPLE_OAUTH_CLIENT_ID: "%s"
  APPLE_OAUTH_CLIENT_SECRET: "%s"
  
  # Session configuration
  SESSION_SECRET_KEY: "%s"
' \
  "${VECTOR_DB_TYPE:-weaviate-local}" \
  "${VECTOR_DB_TEXT_COLLECTION_NAME:-ragme-text-docs}" \
  "${VECTOR_DB_IMAGE_COLLECTION_NAME:-ragme-image-docs}" \
  "${APPLICATION_NAME:-RAGme Kubernetes}" \
  "${APPLICATION_VERSION:-1.0.0}" \
  "${APPLICATION_TITLE:-RAGme AI Assistant}" \
  "${APPLICATION_DESCRIPTION:-AI-powered document and image processing assistant}" \
  "${WATCH_DIRECTORY:-/app/watch_directory}" \
  "${MINIO_LOCAL_PATH:-/app/minio_data}" \
  "${OPENAI_API_KEY}" \
  "${WEAVIATE_API_KEY:-}" \
  "${WEAVIATE_URL:-}" \
  "${MILVUS_URI:-your-milvus-uri}" \
  "${MILVUS_TOKEN:-your-milvus-token}" \
  "${MINIO_ACCESS_KEY:-minioadmin}" \
  "${MINIO_SECRET_KEY:-minioadmin}" \
  "${S3_ENDPOINT:-your-s3-endpoint}" \
  "${S3_ACCESS_KEY:-your-s3-access-key}" \
  "${S3_SECRET_KEY:-your-s3-secret-key}" \
  "${S3_BUCKET_NAME:-your-s3-bucket}" \
  "${S3_REGION:-us-east-1}" \
  "${GOOGLE_OAUTH_CLIENT_ID:-your-google-oauth-client-id}" \
  "${GOOGLE_OAUTH_CLIENT_SECRET:-your-google-oauth-client-secret}" \
  "${GITHUB_OAUTH_CLIENT_ID:-your-github-oauth-client-id}" \
  "${GITHUB_OAUTH_CLIENT_SECRET:-your-github-oauth-client-secret}" \
  "${APPLE_OAUTH_CLIENT_ID:-your-apple-oauth-client-id}" \
  "${APPLE_OAUTH_CLIENT_SECRET:-your-apple-oauth-client-secret}" \
  "${SESSION_SECRET_KEY:-ragme-shared-session-secret-key-2025}" > "$output_file"
}

# Test the function
generate_configmap /tmp/test-configmap-generation.yaml

echo "=== Generated ConfigMap ==="
head -30 /tmp/test-configmap-generation.yaml
echo "..."
echo "=== Checking OPENAI_API_KEY ==="
grep -A 2 -B 2 "OPENAI_API_KEY" /tmp/test-configmap-generation.yaml
