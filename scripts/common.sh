#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export KUBE_CONTEXT=${KUBE_CONTEXT:-k3d-p2p-drive}
export NAMESPACE=${NAMESPACE:-p2p-drive}
export RELEASE=${RELEASE:-tahoe}
export IMAGE=${IMAGE:-p2p-drive/tahoe-lafs:1.20.0-poc}
export CLUSTER=${CLUSTER:-p2p-drive}
export PYTHONUNBUFFERED=1
k() { kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" "$@"; }
