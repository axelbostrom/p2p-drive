#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
kubectl --context "$KUBE_CONTEXT" get nodes >/dev/null
helm_args=("$RELEASE" "$ROOT/charts/tahoe-lafs" --kube-context "$KUBE_CONTEXT"
  --namespace "$NAMESPACE" --create-namespace --wait --timeout 300s
  --set-string "image.repository=${IMAGE%:*}" --set-string "image.tag=${IMAGE##*:}")
# On later runs keep the grid enabled; do not briefly tear down storage pods.
enabled=false
if k get secret tahoe-introducer >/dev/null 2>&1; then enabled=true; fi
helm upgrade --install "${helm_args[@]}" --set "gridEnabled=$enabled"
# Copy the generated capability directly to a Secret, never to stdout or Git.
# A short retry covers the interval between a listening Tub and its FURL file.
python3 "$ROOT/scripts/bootstrap.py"
helm upgrade --install "${helm_args[@]}" --set gridEnabled=true
python3 "$ROOT/scripts/demo.py" wait
k get pods -o wide
