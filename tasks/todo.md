# TODO — Vibe Shield

## Fatto (2026-07-06)
- [x] desiderata.md confermato con l'utente (plugin, blindatura automatica, auto-fix guidato)
- [x] Verifica formato plugin Claude Code (plugin.json, marketplace.json, skills, agents, hooks)
- [x] Manifest plugin + marketplace per installazione
- [x] 6 skill: security-audit, pre-deploy, fix-security, secrets-scan, setup-security, security-help
- [x] 4 agenti: secret-scanner, code-auditor, dependency-auditor, config-auditor
- [x] Hook: PreToolUse su Bash (guard commit e push/deploy), PostToolUse su Write|Edit
- [x] Script bash autonomi con fallback jq/python3/node e fail aperto
- [x] Test end to end degli script su repo git temporanei (17 casi)
- [x] README in italiano

## Fatto (2026-07-06, v0.2.0)
- [x] Agente finding-verifier (verifica incrociata avversariale di ogni finding critico/alto/medio)
- [x] Gate più severo: bloccano anche i problemi MEDI (security-audit, pre-deploy, fix-security, README)
- [x] Agenti su modello migliore disponibile (`model: fable`) con override per singolo audit
- [x] Ambito esteso a qualsiasi sviluppo, non solo vibe coding (wording di agenti, skill, README, manifest)

## Fatto (2026-07-06, v0.3.0)
- [x] Skill second-opinion: secondo parere opzionale di altri provider (Gemini CLI, Codex CLI, Ollama), spenta di default, consenso privacy per i cloud, consultiva (gate invariato)

## Fatto (2026-07-06, v0.4.0)
- [x] COLLAUDO in sessione reale superato: plugin caricato (9 skill, 5 agenti), hook bloccante verificato end to end, alias `fable` accettato
- [x] Fix da collaudo: guard-commit gestisce i comandi composti "git add && git commit" (prima il blocco non scattava a stage vuoto)
- [x] Allowlist falsi positivi (.vibe-shield/allowlist) in tutti i guard
- [x] Skill post-deploy-check (verifica sito online dall'esterno)
- [x] Skill incident-response (guida emergenze)
- [x] Template CI GitHub Actions (gitleaks + audit dipendenze) e dependabot, installati da setup-security
- [x] Checklist per stack in security-audit/references/
- [x] Sezione audit periodico nel README

## Da fare
- [ ] Prova interattiva dell'utente su un progetto vero (5 minuti, checklist nell'handoff)
- [ ] Installazione locale definitiva via marketplace (comando pronto, vedi handoff) quando l'utente vuole
- [ ] RINVIATO su decisione utente (2026-07-06): pubblicazione su GitHub, da affrontare in una sessione dedicata spiegando prima come funzionano i repository
- [ ] Verificare la sintassi non interattiva dei CLI esterni (gemini -p, codex exec, ollama run) quando disponibili
