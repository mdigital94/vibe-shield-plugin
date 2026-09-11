#!/bin/bash
# Known-format scanner: 0 clean, 2 findings, 3 incomplete/error.
set -u
if ! command -v python3 >/dev/null 2>&1; then
  echo "VIBE SHIELD: Python 3 necessario; scansione incompleta." >&2
  exit 3
fi
python3 "$(cd "$(dirname "$0")" && pwd)/secret_scan.py" "$@"

result=$?
case "$result" in
  0|2|3) exit "$result" ;;
  *) echo "VIBE SHIELD: scanner interrotto o non disponibile; controllo incompleto." >&2; exit 3 ;;
esac
