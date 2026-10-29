#!/bin/bash
# Simple deployment helper for Vultr VM
# Usage: ./deploy.sh YOUR_VULTR_INFERENCE_API_KEY

set -e

API_KEY=${1:-$VULTR_INFERENCE_API_KEY}

if [ -z "$API_KEY" ]; then
  echo "Usage: ./deploy.sh <VULTR_INFERENCE_API_KEY>"
  exit 1
fi

echo "Building image..."
docker build -t data-pipeline .

echo "Stopping old container (if any)..."
docker rm -f data-pipeline 2>/dev/null || true

echo "Starting container..."
docker run -d \
  --name data-pipeline \
  -p 8501:8501 \
  -e VULTR_INFERENCE_API_KEY="$API_KEY" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  data-pipeline

echo "Deployed. Open http://$(curl -s ifconfig.me):8501"
