#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
docker build -f "$ROOT/docker/Dockerfile" -t "$IMAGE" "$ROOT"
k3d image import "$IMAGE" --cluster "$CLUSTER"
