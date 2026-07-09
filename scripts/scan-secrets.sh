#!/bin/bash
# Vibe Shield: scanner segreti usato dalle skill (e utilizzabile a mano).
# Uso:
#   scan-secrets.sh [cartella]          scan del working tree (default: cartella corrente)
#   scan-secrets.sh --history [N]       scan degli ultimi N commit (default 50) su tutti i branch
# Output: righe "file:riga: tipo_match(mascherato)". Non stampa MAI il segreto per intero.
set -u

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PLUGIN_ROOT/scripts/lib.sh" || exit 1

MODE="tree"
TARGET="."
LIMIT=50
if [ "${1:-}" = "--history" ]; then
  MODE="history"
  LIMIT="${2:-50}"
elif [ -n "${1:-}" ]; then
  TARGET="$1"
fi

# Maschera: mostra solo i primi 8 caratteri del match
mask() {
  awk -F':' '{
    file=$1; line=$2;
    match_str=$3;
    for (i=4; i<=NF; i++) match_str = match_str ":" $i;
    printf "%s:%s: %.8s****(mascherato)\n", file, line, match_str;
  }'
}

EXCLUDE_RE='\.env\.(example|sample|template|dist)$|(^|/)package-lock\.json$|(^|/)yarn\.lock$|(^|/)pnpm-lock\.yaml$|(^|/)node_modules/|(^|/)\.git/|(^|/)dist/|(^|/)build/'

if [ "$MODE" = "tree" ]; then
  cd "$TARGET" 2>/dev/null || { echo "Cartella non trovata: $TARGET" >&2; exit 1; }
  FOUND=0

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # File tracciati piu' file nuovi non ancora ignorati
    FILES="$( (git ls-files; git ls-files --others --exclude-standard) 2>/dev/null | sort -u )"
  else
    FILES="$(find . -type f \( -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/build/*' \) 2>/dev/null | sed 's|^\./||')"
  fi

  echo "== Segreti nel contenuto dei file =="
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    printf '%s' "$f" | grep -qiE "$EXCLUDE_RE" && continue
    [ -f "$f" ] || continue
    SIZE="$(wc -c < "$f" 2>/dev/null || echo 0)"
    [ "$SIZE" -gt 1000000 ] && continue
    HITS="$(grep -I -n -o -E -f "$VS_PATTERNS_EXACT" "$f" 2>/dev/null | vs_filter_placeholders || true)"
    if [ -n "$HITS" ]; then
      printf '%s\n' "$HITS" | sed "s|^|$f:|" | mask
      FOUND=1
    fi
  done <<EOF_LIST
$FILES
EOF_LIST

  echo ""
  echo "== File con nomi sensibili presenti nel progetto =="
  SENSITIVE="$(printf '%s\n' "$FILES" | grep -iE -f "$VS_PATTERNS_FILES" 2>/dev/null | grep -viE '\.env\.(example|sample|template|dist)$' || true)"
  if [ -n "$SENSITIVE" ]; then
    printf '%s\n' "$SENSITIVE"
    FOUND=1
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      echo ""
      echo "-- Di questi, TRACCIATI da git (grave: finiscono nei commit) --"
      while IFS= read -r s; do
        [ -z "$s" ] && continue
        git ls-files --error-unmatch "$s" >/dev/null 2>&1 && echo "$s"
      done <<EOF_SENS
$SENSITIVE
EOF_SENS
    fi
  else
    echo "(nessuno)"
  fi

  [ "$FOUND" = "0" ] && echo "" && echo "Nessun segreto evidente trovato nel working tree."
  exit 0
fi

# MODE=history: cerca segreti nei commit passati
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Non e' un repository git." >&2; exit 1; }
echo "== Segreti negli ultimi $LIMIT commit (tutti i branch) =="
HISTORY_HITS="$(
  for c in $(git rev-list --all -n "$LIMIT" 2>/dev/null); do
    git grep -I -n -o -E -f "$VS_PATTERNS_EXACT" "$c" -- 2>/dev/null | vs_filter_placeholders | head -20 || true
  done | sort -u | head -60
)"
if [ -n "$HISTORY_HITS" ]; then
  printf '%s\n' "$HISTORY_HITS" | mask
fi
if command -v gitleaks >/dev/null 2>&1; then
  echo ""
  echo "(Suggerimento: gitleaks e' installato, per una scansione storica completa: gitleaks git .)"
fi
[ -z "$HISTORY_HITS" ] && echo "Nessun segreto evidente trovato nella storia recente."
exit 0
