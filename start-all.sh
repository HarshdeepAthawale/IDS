#!/usr/bin/env bash
# Start IDS stack with Docker Compose (backend, frontend, MongoDB).
set -e
cd "$(dirname "$0")"
docker compose up --build -d
