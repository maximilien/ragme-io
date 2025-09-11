#!/bin/bash
# Test script to generate ConfigMap

# Source the .env file
set -a
source .env
set +a

# Test if OPENAI_API_KEY is loaded
echo "OPENAI_API_KEY loaded: ${OPENAI_API_KEY:0:20}..."

# Generate a simple test ConfigMap
printf 'apiVersion: v1
kind: ConfigMap
metadata:
  name: ragme-config
  namespace: ragme
data:
  OPENAI_API_KEY: "%s"
  APPLICATION_NAME: "%s"
' \
  "${OPENAI_API_KEY}" \
  "${APPLICATION_NAME:-RAGme}" > /tmp/test-configmap.yaml

echo "=== Generated ConfigMap ==="
cat /tmp/test-configmap.yaml
