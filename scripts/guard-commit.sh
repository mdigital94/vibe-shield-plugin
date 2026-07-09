#!/bin/bash
# Vibe Shield: guard sul commit.
# Controlla i file che finiranno nel commit: nomi sensibili e possibili segreti nel contenuto.
# IMPORTANTE: l'hook scatta PRIMA che il comando giri. Se il comando e' un composto
# "git add ... && git commit", lo stage e' ancora vuoto al momento del controllo:
# per questo, oltre allo stage, vengono analizzati anche i file che stanno PER essere
# aggiunti (ricavati dagli argomenti di git add, o tutti i modificati con commit -a).
# Se trova rischi concreti, blocca il commit (exit 2) e spiega cosa fare.
# NON stampa mai il valore del segreto trovato.
set -u

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PLUGIN_ROOT/scripts/lib.sh" || exit 0

CMD="${1:-}"

# Se il comando usa "git -C <dir> commit", i controlli vanno fatti in quella
# cartella, non nella cwd della sessione (altrimenti il commit reale sfugge
# al controllo o viene scansionato lo stage sbagliato).
GIT_C_DIR="$(printf '%s' "$CMD" | sed -n 's/.*git[[:space:]]\{1,\}-C[[:space:]]\{1,\}\([^[:space:]]\{1,\}\).*/\1/p')"
if [ -n "$GIT_C_DIR" ]; then
  cd "$GIT_C_DIR" 2>/dev/null || exit 0
fi

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# 1) File gia' in stage
STAGED="$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)"

# 2) File che stanno per entrare con "git add" o "git commit -a" nello stesso comando
EXTRA=""
if printf '%s' "$CMD" | grep -qE 'git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+add[[:space:]]'; then
  ALL_EXTRA="$( { git diff --name-only; git ls-files --others --exclude-standard; } 2>/dev/null | sort -u )"
  # Conta quante volte compare "git add" nel comando: con piu' di un'occorrenza il
  # parsing per singolo comando non e' affidabile (rischio di bypass), quindi si
  # ricade sempre sul fallback prudente che scansiona tutti i file candidati.
  ADD_COUNT="$(printf '%s' "$CMD" | grep -oE 'git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+add[[:space:]]' | wc -l | tr -d ' ')"
  ADD_ARGS="$(printf '%s' "$CMD" | sed -n 's/.*git[[:space:]]\{1,\}add[[:space:]]\{1,\}\([^;&|]*\).*/\1/p')"
  if [ "$ADD_COUNT" = "1" ] && [ -n "$ADD_ARGS" ] && ! printf '%s' "$ADD_ARGS" | grep -qE '(^|[[:space:]])(-A|-a|-u|--all|\.)([[:space:]]|$)' && ! printf '%s' "$ADD_ARGS" | grep -qE '["'"'"']'; then
    for tok in $ADD_ARGS; do
      case "$tok" in -*) continue ;; esac
      tok="${tok%/}"
      EXTRA="$EXTRA
$(printf '%s\n' "$ALL_EXTRA" | grep -E "^$(printf '%s' "$tok" | sed 's/[][\.^$*+?(){}|]/\\&/g')(/|$)" || true)"
    done
  else
    EXTRA="$ALL_EXTRA"
  fi
fi
if printf '%s' "$CMD" | grep -qE 'commit[[:space:]]+[^;&|]*(-[a-zA-Z]*a[a-zA-Z]*|--all)([[:space:]]|$)'; then
  EXTRA="$EXTRA
$(git diff --name-only 2>/dev/null)"
fi

CANDIDATES="$(printf '%s\n%s\n' "$STAGED" "$EXTRA" | grep -v '^$' | sort -u)"
[ -z "$CANDIDATES" ] && exit 0

# 3) Nomi di file sensibili (esclusi i template di esempio)
BAD_FILES="$(printf '%s\n' "$CANDIDATES" \
  | grep -iE -f "$VS_PATTERNS_FILES" 2>/dev/null \
  | grep -viE '\.env\.(example|sample|template|dist)$' \
  | vs_filter_allowlist || true)"

# 4) Possibili segreti nel contenuto (dal disco; se il file non c'e' piu', dalla copia in stage)
BAD_CONTENT=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  printf '%s' "$f" | grep -qiE '\.env\.(example|sample|template|dist)$' && continue
  if [ -f "$f" ]; then
    SIZE="$(wc -c < "$f" 2>/dev/null || echo 0)"
    [ "$SIZE" -gt 1000000 ] && continue
    HIT="$(grep -I -o -E -f "$VS_PATTERNS_EXACT" "$f" 2>/dev/null | vs_filter_placeholders | vs_filter_allowlist || true)"
  else
    HIT="$(git show ":$f" 2>/dev/null | grep -I -o -E -f "$VS_PATTERNS_EXACT" 2>/dev/null | vs_filter_placeholders | vs_filter_allowlist || true)"
  fi
  if [ -n "$HIT" ]; then
    BAD_CONTENT="$BAD_CONTENT
  $f"
  fi
done <<EOF_FILES
$CANDIDATES
EOF_FILES

if [ -z "$BAD_FILES" ] && [ -z "$BAD_CONTENT" ]; then
  exit 0
fi

{
  echo "🛑 VIBE SHIELD: commit BLOCCATO per proteggere l'utente."
  if [ -n "$BAD_FILES" ]; then
    echo ""
    echo "File sensibili in arrivo nel commit (non vanno MAI committati):"
    printf '%s\n' "$BAD_FILES" | sed 's/^/  /'
  fi
  if [ -n "$BAD_CONTENT" ]; then
    echo ""
    echo "File che sembrano contenere segreti veri (chiavi API, password, token):$BAD_CONTENT"
  fi
  echo ""
  echo "COSA FARE ORA (non aggirare il blocco, risolvi la causa):"
  echo "1. Sposta ogni valore segreto in un file .env e verifica che .env sia elencato nel .gitignore."
  echo "2. Nel codice sostituisci il valore con la variabile d'ambiente (es. process.env.NOME_CHIAVE)."
  echo "3. Non aggiungere al commit i file sensibili (e togli dallo stage quelli gia' dentro: git restore --staged <file>)."
  echo "4. Rilancia il commit solo dopo la bonifica."
  echo "5. Se una chiave vera e' finita nel codice, va REVOCATA e rigenerata dal servizio che l'ha emessa: considerala compromessa."
  echo ""
  echo "Per un controllo completo esegui la skill secrets-scan del plugin Vibe Shield."
} >&2

exit 2
