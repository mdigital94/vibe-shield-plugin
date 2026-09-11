#!/bin/bash
# Literal command dispatcher. Python errors fail closed.
set -u
[ "${VIBE_SHIELD_SKIP:-0}" = 1 ] && exit 0
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
command -v python3 >/dev/null 2>&1 || { echo 'VIBE SHIELD: python3 richiesto; controllo bloccato.' >&2; exit 2; }
python3 "$PLUGIN_ROOT/scripts/gate.py" dispatch || exit 2
exit 0
