---
name: secrets-scan
description: Scansione rapida e bonifica guidata dei segreti esposti (chiavi API, password, token) nel codice e nella storia git. Usalo quando l'utente sospetta una chiave esposta, quando un commit viene bloccato dall'hook, o per un controllo veloce senza audit completo.
argument-hint: "[cartella, opzionale]"
---

# Secrets Scan

Trova e bonifica i segreti esposti nel progetto corrente. L'utente non ha competenze tecniche: spiega tutto in italiano semplice e non mostrare mai il valore completo di un segreto.

## Procedura

### 1. Scansione

1. Esegui lo scanner veloce del plugin sul working tree:
   ```
   bash "${CLAUDE_SKILL_DIR}/../../scripts/scan-secrets.sh" ${ARGUMENTS:-.}
   ```
2. Esegui la scansione della storia git recente:
   ```
   bash "${CLAUDE_SKILL_DIR}/../../scripts/scan-secrets.sh" --history 50
   ```
3. Lancia l'agente `secret-scanner` del plugin per la passata approfondita (assegnazioni sospette, casi che i regex non coprono, verifica del .gitignore). Digli cosa hanno già trovato gli script per evitare doppioni.

### 2. Valuta ogni ritrovamento

Per ogni segreto trovato stabilisci la situazione, in ordine di gravità:

1. **Nella storia git di un repo già pubblicato online**: il segreto è compromesso per sempre, anche se lo togli. Serve revoca della chiave E pulizia della storia.
2. **In un file tracciato da git ma mai pushato**: va tolto prima del prossimo push; se il valore è stato incollato anche altrove (chat, screenshot), va rigenerato.
3. **In un file non tracciato o ignorato** (es. .env nel .gitignore): situazione corretta, verifica solo che il .gitignore lo copra davvero (`git check-ignore -v <file>`).

### 3. Bonifica guidata

Per ogni segreto reale, nell'ordine:

1. **Sposta il valore in `.env`** (creandolo se manca) e assicurati che `.env` sia nel `.gitignore`. Aggiorna/crea `.env.example` con il nome della variabile e un valore placeholder.
2. **Sostituisci nel codice** il valore hardcodato con la lettura della variabile d'ambiente, nello stile dello stack (process.env.X, os.environ, import.meta.env per variabili VITE pubbliche, ecc.). Attento: le variabili con prefisso NEXT_PUBLIC_ o VITE_ finiscono nel browser, mai metterci segreti.
3. **Se era in commit passati**: spiega all'utente, in modo semplice, che la chiave va rigenerata dal pannello del servizio (digli quale servizio, in base al tipo di chiave) e che la storia va pulita. Per la pulizia proponi `git filter-repo` (o BFG) SOLO spiegando prima che riscrive la storia: se il repo è condiviso con altri, serve coordinarsi. Non eseguire la riscrittura della storia senza conferma esplicita dell'utente.
4. **Verifica**: rilancia lo scanner e mostra che il risultato è pulito.

### 4. Riassumi

Chiudi con un riepilogo in italiano semplice: cosa hai trovato, cosa hai sistemato tu, cosa deve fare l'utente (tipicamente: rigenerare le chiavi X e Y dai rispettivi siti) e perché è importante farlo subito.
