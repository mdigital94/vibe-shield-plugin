#!/bin/bash
# Invoked in the repository resolved by guard-bash; scans actual index blobs.
set -u
[ "${VIBE_SHIELD_SKIP:-0}" = "1" ] && exit 0
if ! command -v python3 >/dev/null 2>&1; then
  echo "🛑 VIBE SHIELD: Python 3 necessario; controllo commit incompleto." >&2
  exit 2
fi
python3 "$(cd "$(dirname "$0")" && pwd)/commit_scan.py" "${1:-}"

result=$?
[ "$result" -eq 0 ] && exit 0
exit 2
