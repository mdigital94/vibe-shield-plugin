#!/bin/bash
# Vibe Shield: guard su push e deploy.
# Prima di pubblicare online verifica due cose:
#   1. Nessun segreto evidente nei file tracciati dal repo.
#   2. Un audit di sicurezza recente e superato (gate scritto da /pre-deploy o /security-audit
#      in .vibe-shield/status.json). Valido se fatto sullo stesso commit o da meno di 30 minuti.
# Se il gate manca o e' scaduto, blocca (exit 2) e chiede di eseguire /pre-deploy.
set -u

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PLUGIN_ROOT/scripts/lib.sh" || exit 0

IN_GIT=0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && IN_GIT=1

# 1) Scan veloce dei segreti nei file tracciati (solo repo git: git grep e' rapidissimo)
if [ "$IN_GIT" = "1" ]; then
  HITS="$(git grep -I -l -E -f "$VS_PATTERNS_EXACT" -- . 2>/dev/null \
    | grep -viE '\.env\.(example|sample|template|dist)$|(^|/)package-lock\.json$|(^|/)yarn\.lock$|(^|/)pnpm-lock\.yaml$' \
    | vs_filter_allowlist \
    | head -10 || true)"
  if [ -n "$HITS" ]; then
    {
      echo "🛑 VIBE SHIELD: pubblicazione BLOCCATA."
      echo ""
      echo "Questi file tracciati dal repository sembrano contenere segreti (chiavi API, password, token):"
      printf '%s\n' "$HITS" | sed 's/^/  /'
      echo ""
      echo "Se pubblichi ora, chiunque potra' leggerli. COSA FARE:"
      echo "1. Esegui la skill secrets-scan del plugin Vibe Shield per la bonifica guidata."
      echo "2. Sposta i segreti in .env (che deve stare nel .gitignore) e revoca le chiavi esposte."
      echo "3. Se i segreti sono gia' in commit passati, serve anche pulire la storia git: la skill spiega come."
    } >&2
    exit 2
  fi
fi

# 2) Gate: audit recente e superato
STATUS_FILE=".vibe-shield/status.json"
GATE_OK=0
if [ -f "$STATUS_FILE" ]; then
  STATUS_JSON="$(cat "$STATUS_FILE" 2>/dev/null)"
  RESULT="$(vs_json_get "$STATUS_JSON" "result")"
  AUDIT_COMMIT="$(vs_json_get "$STATUS_JSON" "commit")"
  AUDIT_EPOCH="$(vs_json_get "$STATUS_JSON" "epoch")"
  if [ "$RESULT" = "pass" ]; then
    if [ "$IN_GIT" = "1" ] && [ -n "$AUDIT_COMMIT" ] && [ "$AUDIT_COMMIT" = "$(git rev-parse HEAD 2>/dev/null)" ]; then
      GATE_OK=1
    elif [ -n "$AUDIT_EPOCH" ] && printf '%s' "$AUDIT_EPOCH" | grep -qE '^[0-9]+$'; then
      NOW="$(date +%s)"
      AGE=$((NOW - AUDIT_EPOCH))
      [ "$AGE" -ge 0 ] && [ "$AGE" -lt 1800 ] && GATE_OK=1
    fi
  fi
fi

if [ "$GATE_OK" = "0" ]; then
  {
    echo "🛑 VIBE SHIELD: pubblicazione BLOCCATA, manca un audit di sicurezza valido."
    echo ""
    echo "Prima di mettere il progetto online serve un controllo completo e superato."
    echo "COSA FARE: esegui la skill pre-deploy del plugin Vibe Shield (comando /pre-deploy)."
    echo "L'audit e' valido per 30 minuti oppure finche' il codice non cambia (stesso commit)."
    echo "Se l'audit trova problemi, la skill fix-security li corregge in modo guidato."
  } >&2
  exit 2
fi

exit 0
