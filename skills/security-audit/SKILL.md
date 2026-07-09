---
name: security-audit
description: Audit di sicurezza completo del progetto con agenti paralleli (segreti, codice, dipendenze, configurazioni) e verifica incrociata avversariale dei problemi trovati. Usalo quando l'utente chiede di controllare la sicurezza, chiede "è sicuro?", vuole un report, o prima di pubblicare. Produce un report in italiano semplice e il gate per il deploy.
argument-hint: "[cartella o area da controllare, opzionale] [modello, opzionale]"
---

# Security Audit

Esegui un audit di sicurezza completo del progetto corrente (o dell'area indicata in $ARGUMENTS se specificata). Vale per qualsiasi tipo di progetto, dal vibe coding allo sviluppo professionale. Adatta le spiegazioni all'utente: per default italiano semplice, comprensibile anche a chi non programma.

## Scelta del modello

Gli agenti del plugin sono configurati per usare il modello migliore disponibile (campo `model` nei file degli agenti), indipendentemente dal modello della sessione. Regole:

- Se l'utente ha chiesto un modello specifico (negli argomenti o nella conversazione), passa quel modello come override a TUTTI gli agenti che lanci.
- Altrimenti non passare override: vale il modello definito in ogni agente.
- Se il lancio di un agente fallisce perché il modello configurato non è disponibile per l'account, rilancia senza override (eredita la sessione) e segnala la cosa all'utente a fine audit.

## Procedura

### 1. Ricognizione veloce

Identifica lo stack leggendo i file chiave (package.json, requirements.txt, file di config di piattaforma, struttura cartelle). Poi leggi `${CLAUDE_SKILL_DIR}/references/stack-checklists.md` e seleziona le sezioni pertinenti allo stack trovato: le passerai agli agenti come contesto aggiuntivo.

### 2. Lancia i 4 agenti in parallelo

Lancia in un unico blocco, in parallelo, questi quattro agenti del plugin, passando a ciascuno: lo stack rilevato, la cartella radice del progetto e l'eventuale area richiesta:

- `secret-scanner`: segreti esposti nel codice e nella storia git
- `code-auditor`: vulnerabilità nel codice (OWASP Top 10)
- `dependency-auditor`: dipendenze vulnerabili o sospette
- `config-auditor`: configurazioni pericolose (CORS, header, RLS Supabase, regole Firebase, Docker, CI)

Ogni agente restituisce finding nel formato standard con GRAVITA, DOVE, PROBLEMA, SPIEGAZIONE, RISCHIO, FIX, AUTO_FIX e una riga TOTALI.

### 3. Consolida

- Unisci i finding, elimina i duplicati (lo stesso problema segnalato da due agenti conta una volta, con la gravità più alta).
- Ordina per gravità: CRITICO, ALTO, MEDIO, BASSO.

### 4. Verifica incrociata avversariale

Ogni finding CRITICO, ALTO o MEDIO passa al vaglio dell'agente `finding-verifier`, che cerca attivamente di smentirlo leggendo il codice reale:

- Lancia un'istanza di `finding-verifier` per finding, in parallelo (a blocchi di massimo 8 alla volta se sono tanti). Passa a ogni istanza il finding completo e il contesto dello stack.
- Applica i verdetti: CONFERMATO resta (con l'eventuale gravità corretta indicata dal verificatore); SMENTITO esce dal conteggio e finisce in appendice al report con la motivazione; INCERTO resta nel conteggio con la gravità originale, marcato come "da confermare".
- I finding BASSO non passano la verifica (non bloccano nulla): restano come segnalati.

### 5. Scrivi il report e il gate

1. Scrivi il report completo in `.vibe-shield/report.md` con questa struttura: data, commit, riepilogo dei totali post-verifica, i finding raggruppati per gravità nel formato standard (con il verdetto della verifica), e in appendice i finding smentiti con motivazione.
2. Calcola il risultato: `pass` solo se dopo la verifica ci sono ZERO finding critici, ZERO alti e ZERO medi. Altrimenti `fail`.
3. Scrivi il gate eseguendo lo script del plugin:

```
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" <pass|fail> <critici> <alti> <medi> <bassi>
```

Il gate sblocca push e deploy per 30 minuti o finché il commit non cambia.

### 6. Riassumi all'utente

Presenta il risultato in linguaggio adatto all'utente (default: italiano semplice):

- Prima riga: esito secco. Esempio: "🔴 Trovati 2 problemi gravi e 1 medio: per ora NON pubblicare" oppure "🟢 Nessun problema rilevante: puoi pubblicare".
- Poi i problemi critici, alti e medi, uno per uno, ciascuno con: cosa succede in pratica se non lo risolvi (una frase) e la correzione proposta. Indica quali sono stati confermati dalla verifica incrociata e quali restano incerti.
- Dei bassi di' solo quanti sono e che stanno nel report.
- Chiudi offrendo il passo successivo: se ci sono finding con AUTO_FIX SI, proponi di eseguire la skill `fix-security` per correggerli subito.
- Solo se l'utente ha chiesto esplicitamente un secondo parere di altri modelli AI (GPT, Gemini, open source), esegui dopo l'audit la skill `second-opinion`. Mai proporla o eseguirla di tua iniziativa: è una funzione opzionale, spenta di default.

## Regole

- Non mostrare MAI il valore completo di un segreto, nemmeno nel report: mascheralo.
- Non minimizzare: se c'è un critico, un alto o un medio, il messaggio è "non pubblicare finché non è risolto".
- Non allarmare a vuoto: la verifica incrociata serve esattamente a questo; un audit pulito è un buon risultato.
