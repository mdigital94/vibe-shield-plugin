---
name: post-deploy-check
description: Verifica il sito o l'app GIA' pubblicati, dall'esterno, come li vedrebbe un attaccante o un bot: header di sicurezza, file sensibili raggiungibili, informazioni trapelate. Usalo dopo un deploy, quando l'utente chiede "il mio sito online è sicuro?", o come complemento di pre-deploy.
argument-hint: "[URL del sito, es. https://miosito.com]"
---

# Post-Deploy Check

Controlla dall'esterno un sito o un'app già online. Il pre-deploy controlla il codice prima della pubblicazione; questo controllo verifica il risultato finale così com'è esposto a internet.

## Regole di ingaggio (obbligatorie, prima di tutto)

- Verifica SOLO siti di proprietà dell'utente o per cui l'utente ha autorizzazione esplicita. Se l'URL non è chiaramente suo, chiediglielo prima di procedere.
- Solo richieste passive e leggere: normali GET/HEAD come farebbe un browser, poche decine al massimo. NIENTE fuzzing massivo, brute force, injection attive o test che possano danneggiare o sovraccaricare il sito, nemmeno se di proprietà dell'utente.

## Procedura

L'URL è in $ARGUMENTS; se manca, chiedilo. Usa `curl` con timeout brevi (`-m 10`) e user agent normale.

### 1. Header di sicurezza

`curl -sI <url>` e valuta:

- Strict-Transport-Security presente (su https)
- Content-Security-Policy presente (segnala assenza come MEDIO, non ALTO: su siti semplici è comune)
- X-Content-Type-Options: nosniff
- X-Frame-Options o CSP frame-ancestors (protezione clickjacking)
- Referrer-Policy
- Header troppo loquaci: Server o X-Powered-By con versioni precise (es. "Express", "PHP/8.1.2")
- Redirect da http a https attivo (`curl -sI http://...`)

### 2. File che non dovrebbero essere raggiungibili

Verifica che questi percorsi rispondano 404 (o 403), NON 200 con contenuto:

```
/.env  /.env.local  /.env.production
/.git/HEAD  /.git/config
/config.json  /credentials.json
/backup.sql  /dump.sql  /db.sqlite  /database.sqlite
/.DS_Store  /composer.lock (per stack PHP)
/server.js  /app.py (i sorgenti non vanno serviti su siti statici)
```

Attenzione alle SPA: molte rispondono 200 con la index.html a QUALSIASI percorso. Non basta il codice 200: controlla che il contenuto sia davvero il file richiesto (es. `/.git/HEAD` che risponde `ref: refs/heads/...` è grave; che risponde con l'HTML dell'app è un falso allarme).

### 3. Informazioni trapelate

- Sourcemap esposte: nella pagina principale individua i bundle JS e verifica se `<bundle>.js.map` risponde 200 (codice sorgente leggibile da chiunque).
- Nel HTML e nei bundle principali: chiavi API hardcodate (pattern tipo sk_live, AIza, service_role). Ricorda: la chiave anon di Supabase e le chiavi pubbliche (pk_) sono normali nel frontend.
- Pagine di errore: una richiesta a un percorso inesistente non deve mostrare stack trace o percorsi interni del server.
- Cookie impostati dal sito: flag Secure, HttpOnly, SameSite (visibili negli header Set-Cookie).

### 4. API (se il progetto ne espone)

Se conosci gli endpoint dal codice del progetto: verifica che quelli protetti rispondano 401/403 senza credenziali (UNA richiesta senza auth per endpoint, niente di più). Un endpoint che restituisce dati personali senza login è CRITICO.

### 5. Report

Riassumi in italiano semplice con le solite gravità (CRITICO, ALTO, MEDIO, BASSO):

- Cosa è esposto e cosa rischia in pratica.
- Per ogni problema: dove si corregge, distinguendo tra codice del progetto (rilancia fix-security) e pannello della piattaforma (spiega dove cliccare, in breve).
- Aggiungi la sezione "Controllo post-deploy" a `.vibe-shield/report.md` con data, URL e risultati.
- Se emerge un problema CRITICO (es. .env raggiungibile), di' chiaramente che va sistemato SUBITO e che le chiavi eventualmente esposte vanno rigenerate: essendo già online, considerale compromesse.
