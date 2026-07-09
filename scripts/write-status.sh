#!/bin/bash
# Vibe Shield: scrive il gate .vibe-shield/status.json nel progetto corrente.
# Va eseguito dalle skill security-audit e pre-deploy al termine dell'audit.
# Uso: write-status.sh <pass|fail> <n_critici> <n_alti> <n_medi> <n_bassi>
set -u

RESULT="${1:-fail}"
CRIT="${2:-0}"
HIGH="${3:-0}"
MED="${4:-0}"
LOW="${5:-0}"

case "$RESULT" in
  pass|fail) ;;
  *) echo "Uso: write-status.sh <pass|fail> <critici> <alti> <medi> <bassi>" >&2; exit 1 ;;
esac

COMMIT=""
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"

mkdir -p .vibe-shield
cat > .vibe-shield/status.json <<EOF_JSON
{
  "result": "$RESULT",
  "epoch": "$(date +%s)",
  "date": "$(date '+%Y-%m-%d %H:%M:%S')",
  "commit": "$COMMIT",
  "findings": {
    "critici": $CRIT,
    "alti": $HIGH,
    "medi": $MED,
    "bassi": $LOW
  }
}
EOF_JSON

# .vibe-shield contiene report interni: meglio non committarli
if [ -f .gitignore ] && ! grep -q '^\.vibe-shield/$' .gitignore 2>/dev/null; then
  echo ".vibe-shield/" >> .gitignore
elif [ ! -f .gitignore ]; then
  echo ".vibe-shield/" > .gitignore
fi

echo "Gate scritto: .vibe-shield/status.json (result=$RESULT, validita': 30 minuti o stesso commit)"
