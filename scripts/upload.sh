#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
exec python3 "$ROOT/scripts/demo.py" upload "$@"
