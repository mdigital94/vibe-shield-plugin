# Vibe Shield — Guida per i tester

Grazie per il test. Vibe Shield è un plugin per Claude Code che blinda i progetti prima della pubblicazione: scansione segreti, audit OWASP con verifica avversariale, blocco automatico di commit e deploy a rischio, fix guidati. Target: anche utenti non tecnici (vibe coding), quindi i report sono in italiano semplice. Sotto il cofano: 9 skill, 5 agenti specializzati, hook PreToolUse/PostToolUse con script bash puri.

## Requisiti

- Claude Code (CLI) su macOS o Linux, versione recente (`claude --version`, testato su 2.1.198).
- Nessuna dipendenza obbligatoria. Se hai gitleaks, pip-audit ecc., il plugin li sfrutta.

## Installazione (2 minuti)

1. Scompatta la cartella dove preferisci.
2. In una sessione Claude Code qualsiasi:
   ```
   /plugin marketplace add /percorso/della/cartella/scompattata
   /plugin install vibe-shield@vibe-shield-marketplace
   /reload-plugins
   ```
3. Verifica: `/vibe-shield:security-help` deve rispondere.

Per disinstallare: `/plugin uninstall vibe-shield` e `/plugin marketplace remove vibe-shield-marketplace`.

## Percorso di test suggerito

Su un progetto di prova (o una copia di uno vero):

1. `/vibe-shield:setup-security` — blindatura preventiva
2. Chiedi a Claude di scrivere in un file una chiave finta con formato reale (es. `sk_live_...` di 24+ caratteri): deve arrivare subito l'avviso dell'hook
3. Chiedi a Claude di committare quel file: il commit deve essere BLOCCATO (anche con `git add X && git commit` in un comando solo)
4. Chiedi di fare push: deve essere bloccato finché `/vibe-shield:pre-deploy` non passa
5. `/vibe-shield:security-audit` su un progetto con vulnerabilità note (SQL concatenato, CORS *, RLS assente...) e valuta qualità e falsi positivi del report
6. Se hai un tuo sito online: `/vibe-shield:post-deploy-check https://tuosito.tld`

## Quello che ci interessa davvero: prova a romperlo

Sei esperto di sicurezza: fai red teaming delle protezioni.

- Formati di segreti che sfuggono ai pattern (`scripts/patterns-exact.grep`)
- Modi di committare o pubblicare che aggirano gli hook (comandi composti, alias, script intermedi, tool diversi da Bash)
- Falsi positivi fastidiosi (c'è l'allowlist in `.vibe-shield/allowlist`, una ERE per riga)
- Prompt injection: un file malevolo nel progetto può convincere gli agenti a ignorare o falsificare un finding?
- Qualità dell'audit: finding gonfiati, mancati, gravità sbagliate; efficacia del verificatore avversariale
- Robustezza degli script (`scripts/`): parsing JSON, fail-open abusabile, edge case git

Nota dichiarata: gli hook proteggono solo ciò che passa da Claude Code; per il resto c'è il template CI (`templates/security-ci.yml`). Il bypass documentato `VIBE_SHIELD_SKIP=1` è una scelta consapevole di design.

## Feedback

Segnala per ogni problema: cosa hai fatto, cosa ti aspettavi, cosa è successo (con output). Anche due righe vanno benissimo. Grazie!
