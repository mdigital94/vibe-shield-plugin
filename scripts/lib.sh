#!/bin/bash
# Vibe Shield: helper condivisi per gli hook.
# Filosofia: mai rompere il flusso dell'utente per un errore interno.
# Se qualcosa va storto negli helper, si "fallisce aperto" (exit 0),
# tranne quando abbiamo GIA' trovato un rischio concreto.

# Estrae un campo stringa da un JSON usando il primo parser disponibile.
# Uso: vs_json_get "$JSON" "tool_input.command"
vs_json_get() {
  local json="$1" path="$2"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$json" | jq -r --arg p "$path" 'getpath($p | split(".")) // empty' 2>/dev/null
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$json" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    for k in sys.argv[1].split("."):
        d = d[k]
    if isinstance(d, str):
        print(d)
except Exception:
    pass
' "$path" 2>/dev/null
    return
  fi
  if command -v node >/dev/null 2>&1; then
    printf '%s' "$json" | node -e '
let s = "";
process.stdin.on("data", c => s += c);
process.stdin.on("end", () => {
  try {
    let d = JSON.parse(s);
    for (const k of process.argv[1].split(".")) d = d[k];
    if (typeof d === "string") process.stdout.write(d);
  } catch (e) {}
});
' "$path" 2>/dev/null
    return
  fi
  echo "⚠️ VIBE SHIELD: nessun parser JSON disponibile (jq, python3 o node): i controlli su questa azione sono DISATTIVATI. Installa uno dei tre per riattivarli." >&2
  printf ''
}

# Filtra le righe che sono chiaramente placeholder o esempi, non segreti veri.
vs_filter_placeholders() {
  grep -viE '(user(name)?:pass(word)?|<[a-z_ -]+>|\$\{[^}]*\}|\byour[_-]?|\bexample\b|\bchangeme\b|\bplaceholder\b|xxxx+|\*\*\*|\bTODO\b|\bFIXME\b|\binserisci\b|\bla[_-]?tua[_-]?)' 2>/dev/null
}

# Filtra i falsi positivi accettati dall'utente.
# File: .vibe-shield/allowlist nel progetto, una espressione regolare (ERE) per riga,
# righe vuote e commenti (#) ignorati. Una riga che matcha il testo del finding
# (contenuto o percorso del file) lo sopprime. Va usato con giudizio: e' pensato
# per i falsi allarmi ricorrenti, non per zittire problemi veri.
# Ogni pattern viene validato prima dell'uso: una regex non valida, o un pattern
# cosi' ampio da matchare un testo "canarino" senza alcuna relazione con un vero
# segreto, viene scartato con un avviso invece di azzerare in silenzio i finding.
vs_filter_allowlist() {
  local al=".vibe-shield/allowlist" raw line ok=""
  if [ ! -f "$al" ]; then
    cat
    return
  fi
  raw="$(grep -vE '^[[:space:]]*(#|$)' "$al" 2>/dev/null)"
  if [ -z "$raw" ]; then
    cat
    return
  fi
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    printf '' | grep -E "$line" >/dev/null 2>&1
    rc=$?
    if [ "$rc" = "2" ]; then
      echo "⚠️ VIBE SHIELD: pattern allowlist non valido, ignorato" >&2
      continue
    fi
    if printf 'VIBE_SHIELD_CANARIO_9f3a7c21_non_e_un_segreto_reale' | grep -qE "$line" 2>/dev/null; then
      echo "⚠️ VIBE SHIELD: pattern allowlist troppo ampio, rifiutato per sicurezza" >&2
      continue
    fi
    ok="$ok
$line"
  done <<EOF_PATTERNS
$raw
EOF_PATTERNS
  ok="$(printf '%s\n' "$ok" | grep -v '^$')"
  if [ -n "$ok" ]; then
    grep -v -E -f <(printf '%s\n' "$ok") 2>/dev/null
  else
    cat
  fi
}

# Directory con i pattern dei segreti (relativa a questo file).
VS_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VS_PATTERNS_EXACT="$VS_SCRIPTS_DIR/patterns-exact.grep"
VS_PATTERNS_FILES="$VS_SCRIPTS_DIR/patterns-files.grep"
