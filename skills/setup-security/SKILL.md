---
name: setup-security
description: Blindatura preventiva di un progetto: .gitignore corretto, gestione dei segreti con .env, security header, difese di base per lo stack rilevato. Usalo all'inizio di un progetto nuovo, quando si installa il plugin su un progetto esistente, o quando l'utente chiede di "mettere in sicurezza" il progetto.
---

# Setup Security

Porta il progetto corrente a uno stato di sicurezza di base, in una sola passata. Prevenire costa meno che bonificare: questa skill va eseguita idealmente all'inizio del progetto. L'utente non ha competenze tecniche: applica le protezioni e spiegagliele in breve alla fine.

## Procedura

### 1. Rileva lo stack

Leggi package.json, requirements.txt, file di config presenti, struttura cartelle. Adatta i passi seguenti a ciò che trovi: non aggiungere protezioni per tecnologie che il progetto non usa.

### 2. Fondamenta (per qualsiasi progetto)

1. **`.gitignore`**: crea o integra con almeno: `.env*` (con eccezione `!.env.example`), `node_modules/`, cartelle di build, `*.pem`, `*.key`, `credentials.json`, `serviceAccountKey.json`, `.vibe-shield/`, file di log e dump (`*.log`, `*.sql`, `*.dump`).
2. **Gestione segreti**: se nel codice ci sono valori hardcodati che sembrano segreti, spostali in `.env` e sostituiscili con variabili d'ambiente. Crea `.env.example` con i nomi delle variabili e placeholder.
3. **Se il repo git esiste già**: verifica con `git ls-files` che nessun file sensibile sia già tracciato; se lo è, esegui la bonifica come da skill `secrets-scan`.
4. **Cartella `.vibe-shield/`**: creala (per report e gate degli audit).

### 3. Difese per stack (applica solo le pertinenti)

**Next.js / React / Vite (frontend + API)**
- Security header nella config (next.config headers, vercel.json, netlify.toml o \_headers): X-Content-Type-Options nosniff, X-Frame-Options DENY (o frame-ancestors), Referrer-Policy strict-origin-when-cross-origin, HSTS se dominio con https. CSP se praticabile senza rompere l'app.
- Ricorda nel codice: mai segreti in variabili NEXT_PUBLIC_ o VITE_.

**Express / Node backend**
- helmet, rate limiting sulle rotte di auth (express-rate-limit), CORS con lista esplicita di origin, cookie di sessione con HttpOnly+Secure+SameSite, limite dimensione body.

**Python (FastAPI/Flask/Django)**
- DEBUG spento in produzione, SECRET_KEY da variabile d'ambiente, CORS con origin espliciti, ALLOWED_HOSTS configurato (Django).

**Supabase**
- Verifica che ogni tabella abbia RLS abilitata e policy sensate; se mancano, proponi policy di partenza (l'utente deve confermare chi può vedere cosa: è una decisione sua).
- service_role SOLO lato server, mai in file esposti al browser.

**Firebase**
- Regole di sicurezza non aperte (`if true`): proponi regole basate su auth.

**Docker**
- Utente non root, .dockerignore con .env e .git, niente segreti in ENV nel Dockerfile.

**GitHub**
- Se il progetto è (o sarà) su GitHub, copia i template del plugin:
  - `${CLAUDE_SKILL_DIR}/../../templates/dependabot.yml` in `.github/dependabot.yml` (aggiornamenti di sicurezza automatici delle dipendenze; togli gli ecosistemi che il progetto non usa)
  - `${CLAUDE_SKILL_DIR}/../../templates/security-ci.yml` in `.github/workflows/security.yml` (scansione segreti e dipendenze a ogni push, anche quando le modifiche non passano da Claude Code)
- Suggerisci di attivare il secret scanning del repo nelle impostazioni GitHub.

### 4. Verifica e riepilogo

1. Se il progetto ha build o test, eseguili: le protezioni non devono rompere nulla.
2. Riassumi in italiano semplice cosa hai messo in piedi, con una frase sul perché per ogni protezione.
3. Spiega in tre righe come funziona d'ora in poi la protezione automatica: i commit con segreti vengono bloccati, prima di pubblicare serve il controllo `pre-deploy`, e con `security-audit` si può controllare tutto in qualsiasi momento.
