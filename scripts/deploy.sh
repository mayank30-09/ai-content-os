#!/usr/bin/env bash
# Production Container Deployment Script for AI Content OS
set -euo pipefail

ENV=${1:-production}
echo "[DEPLOY] Starting deployment for environment: ${ENV}"

if [ "${ENV}" = "production" ]; then
    docker compose -f docker/docker-compose.prod.yml up -d --build
else
    docker compose -f docker/docker-compose.yml up -d --build
fi

echo "[DEPLOY] Deployment command issued successfully."
