#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
exec kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" port-forward \
  --address 127.0.0.1 "pod/$RELEASE-client-0" "${PORT:-3456}:3456"
