# DESIDERATA — Vibe Shield (plugin Claude Code di sicurezza)
> What to build and why. Update incrementally when scope changes. Confirm with the user before building.
> Last updated: 2026-07-06

## 🎯 Goal / problem to solve
Chi sviluppa via vibe coding (nessuna competenza tecnica) pubblica online o su GitHub codice potenzialmente pieno di falle: segreti esposti, vulnerabilità, configurazioni pericolose. Serve uno strumento che controlli e blindi automaticamente qualsiasi progetto prima che vada in produzione, coprendo rischi voluti e involontari.

## 👥 Users / who it's for
Chiunque sviluppi con Claude Code e pubblichi online (Vercel, Netlify, GitHub, Supabase, Firebase, ecc.): dal vibe coder senza competenze allo sviluppatore professionale. Comunicazione di default in italiano semplice, zero gergo non spiegato. (Ampliato il 2026-07-06: prima era solo vibe coding.)

## 📦 In scope · 🚫 Out of scope (non-goals)
**In scope**
- Plugin Claude Code installabile una volta, valido per ogni progetto.
- Scansione segreti (codice, file di config, storia git) con blocco automatico.
- Audit del codice: OWASP Top 10, injection, XSS, auth rotta, IDOR, SSRF, upload non sicuri.
- Audit dipendenze: vulnerabilità note, pacchetti sospetti.
- Audit configurazioni: CORS, security header, cookie, debug mode, RLS Supabase, regole Firebase, Docker, CI.
- Hook automatici: blocco su commit e push/deploy. Gate severo: passa solo con zero problemi critici, alti e medi.
- Verifica incrociata avversariale: ogni problema critico/alto/medio viene ricontrollato da un agente indipendente (finding-verifier) che cerca di smentirlo.
- Scelta del modello: gli agenti usano il modello migliore disponibile (default `fable`), non quello della sessione; override per singolo audit su richiesta.
- Auto-fix guidato: correzione automatica di ciò che è sicuro correggere, spiegazione semplice per il resto.
- Setup preventivo di un progetto nuovo (gitignore, .env.example, header, ecc.).

**Out of scope**
- Pentest attivo o scanning di infrastrutture esterne.
- Monitoraggio runtime in produzione.
- Garanzia assoluta: il plugin riduce drasticamente il rischio, non lo azzera.

## ⭐ Features — must-have
- Distribuzione come plugin Claude Code (repo installabile via marketplace).
- Hook PreToolUse bloccanti: scan segreti prima di `git commit`, gate completo prima di `git push` e comandi di deploy.
- Skill `/security-audit` (audit completo con agenti paralleli), `/secrets-scan`, `/fix-security` (auto-fix guidato), `/pre-deploy` (gate finale), `/setup-security` (blindatura preventiva).
- Agenti specializzati: secret scanner, code auditor, dependency auditor, config auditor.
- Report in italiano, linguaggio semplice, con gravità chiara (critico, alto, medio, basso).
- Script hook autonomi (bash/python stdlib), nessuna dipendenza esterna obbligatoria.

## ✨ Features — nice-to-have
- Secondo parere di modelli di altri provider (skill second-opinion): opzionale, spento di default, solo su richiesta esplicita. Usa i CLI installati (Gemini, Codex, Ollama locale), con consenso privacy per i cloud, segreti mascherati prima dell'invio, esito consultivo (il gate non cambia).
- Uso di tool esterni se presenti (gitleaks, semgrep, npm audit, pip-audit) con fallback interno.
- Checklist per stack specifici (Next.js, Supabase, Firebase, Express, siti statici).
- Badge o file di stato (`.security-audit.json`) che certifica l'ultimo audit superato.

## 📐 Constraints (tech, time, budget, compliance)
- Deve funzionare senza installazioni aggiuntive (solo Claude Code su macOS/Linux).
- Gli script hook devono essere veloci (secondi, non minuti) per non degradare l'esperienza.
- Nessun segreto deve mai finire nei log o nei report.
- Enforcement scelto dall'utente: blindatura automatica bloccante sui rischi critici.
- Remediation scelta: auto-fix guidato (fix sicuri automatici, decisioni umane spiegate in modo semplice).

## ✅ Success criteria (how we know it works / is done)
- Installando il plugin in un progetto qualsiasi, un commit con una chiave API viene bloccato automaticamente.
- Un push o deploy con vulnerabilità critiche viene fermato con spiegazione comprensibile.
- `/security-audit` produce un report in italiano semplice con fix applicabili.
- `/setup-security` porta un progetto nuovo a uno stato blindato di base in una passata.

## ❓ Open questions
- Nome definitivo del plugin (proposta di lavoro: "vibe-shield").
- Pubblicazione su GitHub: RINVIATA per decisione utente (2026-07-06), verrà affrontata in una sessione dedicata. Nel frattempo installazione dalla cartella locale.

## 📝 Changelog
- 2026-07-06 (v0.4.0): collaudo in sessione Claude Code reale SUPERATO (plugin caricato, hook bloccanti verificati end to end, alias fable accettato). Fix importante emerso dal collaudo: la guardia commit ora analizza anche i file che stanno per essere aggiunti nei comandi composti "git add X && git commit" (prima lo stage era vuoto al momento del controllo e il blocco non scattava). Aggiunti: allowlist falsi positivi (.vibe-shield/allowlist), skill post-deploy-check (verifica del sito già online, dall'esterno), skill incident-response (emergenze), template CI GitHub Actions + dependabot installati da setup-security, checklist per stack in security-audit.
- 2026-07-06 (v0.3.0): aggiunta skill second-opinion (secondo parere di GPT/Gemini/open source via CLI installati): opzionale, spenta di default, attivabile solo dall'utente. Chiarito che gli agenti girano solo su modelli Claude (vincolo di Claude Code).
- 2026-07-06 (v0.2.0): su richiesta utente: (1) verifica incrociata avversariale con agente finding-verifier, (2) gate più severo, bloccano anche i problemi MEDI, (3) agenti sul modello migliore disponibile (model: fable) invece del modello di sessione, con override possibile, (4) ambito esteso da solo vibe coding a qualsiasi sviluppo.
- 2026-07-06: creazione del documento. Decisioni utente: plugin Claude Code, blindatura automatica bloccante, auto-fix guidato.
