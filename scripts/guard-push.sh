#!/bin/bash
set -u
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
command -v python3 >/dev/null 2>&1 || { echo 'VIBE SHIELD: python3 richiesto.' >&2; exit 2; }
python3 "$PLUGIN_ROOT/scripts/gate.py" publish "${1:-git push}" || exit 2
exit 0
