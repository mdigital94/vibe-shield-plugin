# HANDOFF — Vibe Shield (plugin Claude Code di sicurezza)
> Update at end of session / before /clear and /compact. Read at the start.
> Last updated: 2026-07-06

## 🎯 Goal
Plugin Claude Code (v0.4.0) che blinda automaticamente qualsiasi progetto (vibe coding e sviluppo professionale) prima di pubblicazione online o su GitHub: scan segreti, audit vulnerabilità con verifica incrociata avversariale, blocco automatico di commit/push/deploy a rischio (gate severo: bloccano anche i MEDI), auto-fix guidato. Comunicazione di default in italiano semplice. Dettagli in desiderata.md.

## 📁 Files I'm working on
- `.claude-plugin/plugin.json` + `marketplace.json` (installazione via marketplace)
- `skills/` 9 skill: security-audit (con references/stack-checklists.md), pre-deploy, fix-security, secrets-scan, setup-security, security-help, second-opinion (opzionale, spenta di default), post-deploy-check (verifica sito online dall'esterno, solo siti propri, richieste passive), incident-response (emergenze)
- `templates/` security-ci.yml (GitHub Actions: gitleaks + audit dipendenze) e dependabot.yml, installati da setup-security
- `agents/` 5 agenti: secret-scanner, code-auditor, dependency-auditor, config-auditor, finding-verifier (verifica avversariale). Tutti con `model: fable` nel frontmatter: usano il modello migliore, non quello di sessione
- `hooks/hooks.json` (PreToolUse su Bash, PostToolUse su Write|Edit)
- `scripts/` guard-bash.sh (dispatcher), guard-commit.sh, guard-push.sh, check-write.sh, scan-secrets.sh, write-status.sh, lib.sh, patterns-exact.grep, patterns-files.grep

## ✅ Current state (what works)
- INSTALLATO dall'utente via marketplace locale (2026-07-06): skill, agenti e hook attivi nelle sue sessioni.
- Distribuzione ai tester: creato TESTING.md (guida per esperti di sicurezza, con invito al red teaming) e zip su ~/Desktop/vibe-shield-v0.4.0.zip (esclusi handoff, desiderata, tasks).
- COLLAUDO IN SESSIONE REALE SUPERATO (2026-07-06, claude 2.1.198, non interattivo con --plugin-dir): plugin caricato con tutte le skill e agenti; hook PreToolUse blocca davvero il commit con segreto; agente con model: fable parte senza errori e produce la riga TOTALI.
- Fix chiave emerso dal collaudo: guard-commit ora gestisce i comandi composti "git add ... && git commit" analizzando anche i file che stanno per essere aggiunti (parse degli argomenti di git add, fallback prudente a tutti i modificati+untracked; gestito anche commit -a). Prima il blocco non scattava perché lo stage era vuoto al momento dell'hook. 10 nuovi test di script passati (composti, allowlist).
- Allowlist falsi positivi: .vibe-shield/allowlist (una ERE per riga, # commenti), filtra contenuti e percorsi in guard-commit, guard-push, check-write via vs_filter_allowlist in lib.sh.
- Struttura completa del plugin v0.1.0, JSON validi, sintassi bash ok, script eseguibili.
- Testato end to end con repo git temporanei: commit con chiave AWS bloccato (exit 2), commit pulito passa, .env in stage bloccato, push senza gate bloccato, gate pass sblocca il push, gate fail blocca, VIBE_SHIELD_SKIP=1 bypassa, check-write segnala segreti scritti e .env non ignorato o tracciato, matcher vercel distingue deploy da comandi innocui, scan-secrets maschera i valori.
- Meccanica del gate: le skill security-audit/pre-deploy scrivono `.vibe-shield/status.json` via write-status.sh; guard-push accetta se result=pass e (stesso commit HEAD oppure età < 30 minuti).
- Parsing JSON negli hook: fallback jq → python3 → node, fail aperto se nessuno disponibile.

## ⚠️ What didn't work / constraints
- Exit 141 in un test era solo SIGPIPE causato da `head` nella pipeline di test, non un bug.
- I file .env tracciati da git non vengono coperti dal .gitignore: caso gestito con messaggio dedicato (git rm --cached).
- La chiave anon di Supabase è un JWT pubblico per design: esclusa dai pattern esatti per evitare falsi positivi; il pattern scatta solo su assegnazioni service_role.
- Skill e hook non ancora provati dentro una sessione Claude Code reale (solo script testati direttamente).
- `model: fable` nel frontmatter degli agenti: da verificare in sessione reale che l'alias sia accettato; se non disponibile per l'account, le skill prevedono il fallback al modello di sessione con segnalazione all'utente.
- Aspettative utente gestite: chiede protezione "da migliori hacker del mondo"; comunicato onestamente che contro i bot è realistico, contro attaccanti d'élite nessuno strumento può garantire (vedi README, sezione onestà sul rischio).

## 👉 Next steps (what I'd do next)
1. Installazione locale definitiva (senza GitHub), quando l'utente vuole: in Claude Code eseguire `/plugin marketplace add /Users/matteo/Documents/Progetti_Dev_Personali/Cybersecurity` e poi `/plugin install vibe-shield@vibe-shield-marketplace`. Da quel momento vale in ogni progetto senza --plugin-dir.
2. Prova interattiva breve dell'utente (5 min): su un progetto vero, provare /vibe-shield:setup-security e /vibe-shield:security-audit dal vivo.
3. Pubblicazione su GitHub: RINVIATA su decisione utente (2026-07-06). L'utente non conosce ancora i repository GitHub: quando la affronteremo, partire spiegando le basi (cos'è un repo, pubblico vs privato) prima dei comandi.
4. Verificare su una macchina con i CLI installati la sintassi non interattiva di gemini/codex/ollama usata da second-opinion.
