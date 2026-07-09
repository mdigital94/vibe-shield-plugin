#!/bin/bash
# Vibe Shield: hook PreToolUse su Bash.
# Smista i comandi rilevanti verso il guard giusto:
#   git commit                  -> guard-commit.sh (scan segreti sui file in stage)
#   git push / comandi di deploy -> guard-push.sh  (gate: audit superato + scan veloce)
# Ogni altro comando passa senza rallentamenti.
set -u

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib.sh
. "$PLUGIN_ROOT/scripts/lib.sh" || exit 0

# Via di emergenza documentata nel README: VIBE_SHIELD_SKIP=1 disattiva i blocchi.
[ "${VIBE_SHIELD_SKIP:-0}" = "1" ] && exit 0

INPUT="$(cat)"
CMD="$(vs_json_get "$INPUT" "tool_input.command")"
CWD="$(vs_json_get "$INPUT" "cwd")"
[ -z "$CMD" ] && exit 0
if [ -n "$CWD" ] && [ -d "$CWD" ]; then
  cd "$CWD" 2>/dev/null || exit 0
fi

# git commit (anche con git -C <dir>)
if printf '%s' "$CMD" | grep -qE '(^|[;&|[:space:]])git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?([[:space:]]+-[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'; then
  exec "$PLUGIN_ROOT/scripts/guard-commit.sh" "$CMD"
fi

# git push e comandi di pubblicazione/deploy piu' comuni
if printf '%s' "$CMD" | grep -qE '(^|[;&|[:space:]])(git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+push|vercel[[:space:]]+(deploy|--prod)|vercel[[:space:]]*$|netlify[[:space:]]+deploy|firebase[[:space:]]+deploy|wrangler[[:space:]]+(deploy|publish)|fly(ctl)?[[:space:]]+deploy|railway[[:space:]]+up|render[[:space:]]+deploy|npm[[:space:]]+publish|gh[[:space:]]+(repo[[:space:]]+create|release[[:space:]]+create)|heroku[[:space:]]+(deploy|releases:create)|gcloud[[:space:]]+app[[:space:]]+deploy|amplify[[:space:]]+publish|aws[[:space:]]+s3[[:space:]]+sync|surge([[:space:]]|$))'; then
  exec "$PLUGIN_ROOT/scripts/guard-push.sh" "$CMD"
fi

exit 0
