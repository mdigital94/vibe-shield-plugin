#!/bin/bash
# Vibe Shield: hook PostToolUse su Write ed Edit.
# Dopo ogni scrittura di file controlla due rischi:
#   1. Il file appena scritto contiene un possibile segreto vero fuori da .env.
#   2. E' stato scritto un file .env che NON risulta ignorato da git.
# Non blocca la scrittura (e' gia' avvenuta) ma segnala subito il problema a Claude
# con exit 2, cosi' viene corretto prima che finisca in un commit.
set -u

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PLUGIN_ROOT/scripts/lib.sh" || exit 0

[ "${VIBE_SHIELD_SKIP:-0}" = "1" ] && exit 0

INPUT="$(cat)"
FILE="$(vs_json_get "$INPUT" "tool_input.file_path")"
[ -z "$FILE" ] && FILE="$(vs_json_get "$INPUT" "tool_input.notebook_path")"
CWD="$(vs_json_get "$INPUT" "cwd")"
[ -z "$FILE" ] && exit 0
if [ -n "$CWD" ] && [ -d "$CWD" ]; then
  cd "$CWD" 2>/dev/null || exit 0
fi
[ -f "$FILE" ] || exit 0

# Salta cartelle generate e file grandi o binari
case "$FILE" in
  */node_modules/*|*/.git/*|*/dist/*|*/build/*|*/.next/*|*/vendor/*) exit 0 ;;
esac
SIZE="$(wc -c < "$FILE" 2>/dev/null || echo 0)"
if [ "$SIZE" -gt 500000 ]; then
  echo "⚠️ VIBE SHIELD: controllo immediato incompleto (file grande); esegui secrets-scan prima del commit." >&2
  exit 2
fi

BASENAME="$(basename "$FILE")"

# Caso 1: file .env scritto ma non ignorato da git
case "$BASENAME" in
  .env|.env.*)
    case "$BASENAME" in
      .env.example|.env.sample|.env.template|.env.dist)
        # Template names are safe; credentials inside them still need scanning.
        if grep -a -o -E -f "$VS_PATTERNS_EXACT" "$FILE" 2>/dev/null | vs_filter_placeholders | vs_filter_allowlist | grep -q .; then
          echo "⚠️ VIBE SHIELD: possibile segreto nel template; sostituiscilo con un placeholder." >&2
          exit 2
        fi
        exit 0 ;;
    esac
    DIR="$(dirname "$FILE")"
    if git -C "$DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      if git -C "$DIR" ls-files --error-unmatch "$FILE" >/dev/null 2>&1; then
        {
          echo "⚠️ VIBE SHIELD: $BASENAME risulta TRACCIATO da git: i suoi segreti finiscono nei commit."
          echo "Il .gitignore da solo non basta per i file gia' tracciati. Correggi cosi':"
          echo "1. git rm --cached $BASENAME   (lo toglie da git senza cancellarlo dal disco)"
          echo "2. Aggiungi la riga '.env*' (con eccezione '!.env.example') al .gitignore."
          echo "3. Se il file era gia' stato pushato online, le chiavi al suo interno vanno rigenerate."
        } >&2
        exit 2
      fi
      if ! git -C "$DIR" check-ignore -q "$FILE" 2>/dev/null; then
        {
          echo "⚠️ VIBE SHIELD: hai scritto $BASENAME ma git NON lo sta ignorando."
          echo "Rischio: i segreti dentro $BASENAME possono finire in un commit e poi online."
          echo "Aggiungi subito la riga '.env*' (con eccezione '!.env.example') al file .gitignore del progetto, creandolo se non esiste."
        } >&2
        exit 2
      fi
    fi
    exit 0
    ;;
esac

# Caso 2: possibile segreto vero scritto in un file di codice o config
if grep -I -o -E -f "$VS_PATTERNS_EXACT" "$FILE" 2>/dev/null | vs_filter_placeholders | vs_filter_allowlist | grep -q .; then
  {
    echo "⚠️ VIBE SHIELD: il file appena scritto sembra contenere un segreto vero (chiave API, token o password):"
    echo "  $FILE"
    echo "Correggi subito, prima di qualsiasi commit:"
    echo "1. Sposta il valore in .env (verificando che .env sia nel .gitignore)."
    echo "2. Nel codice usa la variabile d'ambiente al posto del valore."
    echo "3. Se il valore era una chiave reale gia' condivisa o incollata altrove, va rigenerata."
  } >&2
  exit 2
fi

exit 0
