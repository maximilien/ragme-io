#!/bin/bash

# Source the .env file
set -a
source ../.env
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
  # Vector Database Configuration
  VECTOR_DB_TYPE: "%s"
  VECTOR_DB_TEXT_COLLECTION_NAME: "%s"
  VECTOR_DB_IMAGE_COLLECTION_NAME: "%s"
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
  # Required secrets
  OPENAI_API_KEY: "%s"
  WEAVIATE_API_KEY: "%s"
  WEAVIATE_URL: "%s"
  GOOGLE_OAUTH_CLIENT_ID: "%s"
  GITHUB_OAUTH_CLIENT_SECRET: "%s"
  GITHUB_OAUTH_CLIENT_ID: "%s"
  GITHUB_OAUTH_CLIENT_SECRET: "%s"
  SESSION_SECRET_KEY: "%s"
' \
  "${VECTOR_DB_TYPE:-weaviate}" \
  "${VECTOR_DB_TEXT_COLLECTION_NAME:-ragme-text-docs}" \
  "${VECTOR_DB_IMAGE_COLLECTION_NAME:-ragme-image-docs}" \
  "${OPENAI_API_KEY}" \
  "${WEAVIATE_API_KEY:-}" \
  "${WEAVIATE_URL:-}" \
  "${GOOGLE_OAUTH_CLIENT_ID:-your-google-oauth-client-id}" \
  "${GOOGLE_OAUTH_CLIENT_SECRET:-your-google-oauth-client-secret}" \
  "${GITHUB_OAUTH_CLIENT_ID:-your-github-oauth-client-id}" \
  "${GITHUB_OAUTH_CLIENT_SECRET:-your-github-oauth-client-secret}" \
  "${SESSION_SECRET_KEY:-ragme-shared-session-secret-key-2025}" > k8s/configmap-test.yaml

echo "Configmap generated to k8s/configmap-test.yaml"
