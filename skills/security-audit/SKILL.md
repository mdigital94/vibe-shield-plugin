---
name: security-audit
description: Audit del progetto con scanner deterministici, revisione del codice e specialisti quando necessari. Verifica indipendente dei problemi per gruppi correlati. Produce report, copertura esplicita e gate solo per audit completi.
argument-hint: "[cartella o area da controllare, opzionale] [modello, opzionale]"
---

# Security Audit

Controlla il progetto corrente, in italiano semplice salvo diversa richiesta. Un’area indicata in $ARGUMENTS produce un audit **parziale**: documenta i risultati, ma non autorizza l’intero progetto.

## Modello e costo

Gli agenti ereditano il modello della sessione. Rispetta un modello esplicitamente richiesto dall’utente; se non disponibile, dichiara il limite senza sostituirlo silenziosamente. Non forzare il modello più costoso. Usa specialisti per un compito circoscritto che richiede analisi indipendente o competenza specifica, senza avviare automaticamente tutti e quattro gli auditor.

## Procedura

### 1. Ambito e invalidazione

Lavora dalla radice del repository interessato, mai dalla cartella di un altro progetto. Identifica se è un audit completo o parziale. Prima di iniziare invalida l’approvazione precedente e acquisisci l’identità del contenuto con il protocollo gate descritto sotto. Un’interruzione deve lasciare il progetto bloccato.

Leggi una volta i manifest e le configurazioni chiave, individua monorepo, stack, superfici d’attacco e componenti distribuiti. Leggi solo le sezioni pertinenti di `${CLAUDE_SKILL_DIR}/references/stack-checklists.md`. Mantieni una matrice di copertura: segreti e storia Git, dipendenze di ogni stack, codice e logica applicativa, configurazioni. Ogni voce ha esito completa/incompleta/non applicabile, prove e motivazione. Non applicabile richiede una motivazione verificata, non l’assenza di risultati.

### 2. Scanner deterministici prima dell’AI

Esegui lo scanner del plugin sul progetto e sull’intera storia Git:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/scan-secrets.sh" .
bash "${CLAUDE_SKILL_DIR}/../../scripts/scan-secrets.sh" --history --all
```

Esiti dello scanner: `0` nessun match, `2` finding, `3` scansione incompleta/errore. Un limite alla storia o file saltati non costituiscono copertura completa; se la storia non esiste motivane la non applicabilità. Usa strumenti dedicati disponibili per integrare la scansione, con output redatto per non mostrare segreti. Controlla dipendenze con il gestore e il database appropriati (es. npm audit sul lockfile, pip-audit sui requisiti del progetto). Controlla tutti i manifest pertinenti, anche nei sotto-progetti.

Conserva output dettagliati localmente, con segreti oscurati. Al modello passa solo esito, ambito, comando/versione/data e finding con riferimenti. Non riversare log completi nella conversazione. Scanner mancante, errore, database non raggiungibile o output non interpretabile significa **copertura incompleta**, mai “nessuna vulnerabilità”. `pip list --outdated` non è uno scanner di vulnerabilità. Non eseguire installazioni o lifecycle script per semplice ricognizione.

### 3. Revisione semantica e delega mirata

Gli scanner non verificano da soli autorizzazioni, IDOR, logica di business o percorsi tra input e utilizzo. La revisione semantica dei componenti pertinenti è obbligatoria, svolta dal coordinatore o da `code-auditor`. Leggi le checklist degli auditor pertinenti se svolgi tu la loro analisi; non serve lanciarli solo per leggere una checklist.

Delega a `secret-scanner`, `dependency-auditor` o `config-auditor` quando ci sono casi ambigui, più stack o superfici che meritano analisi distinta. Assegna ambiti non sovrapposti e passa inventario, risultati sintetici e riferimenti ai file. Evita di ripetere scansioni già valide dello stesso contenuto. La riduzione delle deleghe non riduce la matrice di copertura richiesta.

Richiedi finding con ID, GRAVITA, DOVE, PROBLEMA, SPIEGAZIONE, RISCHIO, FIX, AUTO_FIX; prove concrete, niente trascrizioni estese. Consolida duplicati e ordina per gravità.

### 4. Verifica indipendente per gruppi

Ogni finding CRITICO, ALTO o MEDIO richiede `finding-verifier`, indipendente da chi lo ha prodotto. Raggruppa da uno a quattro finding correlati per componente, condividendo il contesto; non lanciare un agente per ogni singolo problema per default. Il verificatore legge le prove reali e restituisce un verdetto distinto per ID.

CONFERMATO resta con gravità verificata; SMENTITO esce dal conteggio con motivazione in appendice; INCERTO resta con gravità originale, “da confermare”. Se la verifica non è disponibile o il budget termina, marca l’audit incompleto. I BASSI non richiedono verifica indipendente.

### 5. Report e gate

Scrivi `.vibe-shield/report.md`: data, radice e identità iniziale/finale del contenuto, ambito completo/parziale, matrice di copertura, scanner e relativi esiti, totali dopo verifica, finding con verdetti, smentiti in appendice, limiti e controlli mancanti. Registra agenti effettivamente avviati e riusi. Durata e token sono valori misurati solo se disponibili dall’host; altrimenti scrivi “non disponibile”. Non presentare stime come consumi reali.

`pass` richiede contemporaneamente ambito completo, copertura completa delle aree pertinenti, verifiche completate, zero critici/alti/medi e contenuto invariato dall’inizio. Problemi bloccanti danno `fail`; audit parziale, interrotto, senza strumenti necessari o con contenuti mutati dà `incomplete`. Un audit selettivo delle sole modifiche può aiutare a indagare, ma non conferisce un pass globale. Non riciclare vecchie conclusioni su contenuti cambiati.

Dalla radice del repository, esegui all’inizio:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" begin
```

Il comando invalida il pass e salva lo snapshot iniziale. Al termine, solo per audit completo e concluso con contenuti invariati:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" pass 0 0 0 <bassi> --scope full --complete
```

Per problemi bloccanti o copertura insufficiente:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" fail <critici> <alti> <medi> <bassi>
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" incomplete <critici> <alti> <medi> <bassi>
```

Scegli uno solo degli ultimi due esiti secondo il caso. Controlla il codice d’uscita di ogni comando: uno snapshot cambiato o un errore di scrittura non è un pass. Lo script controlla l’identità, ma la dichiarazione di copertura completa resta responsabilità dell’auditor; non scrivere `--complete` quando mancano controlli. Il pass dura meno di 30 minuti **e** richiede identità invariata; il solo HEAD uguale non basta.

### 6. Esito all’utente

Comunica esito e limiti prima dei dettagli: “Controllo completato, nessun problema bloccante rilevato”, “Non pubblicare: …” oppure “Controllo incompleto: manca …”. Un pass non è una garanzia di sicurezza assoluta. Spiega i problemi critici/alti/medi e il fix proposto, conta i bassi rimandando al report. Se servono correzioni, indica `fix-security` come passo successivo.

Esegui `second-opinion` solo se esplicitamente richiesto. Non mostrare mai segreti completi in output o report. Se scade il budget, conserva risultati e lacune, lascia il gate incompleto: non ridurre silenziosamente la copertura per concludere.
