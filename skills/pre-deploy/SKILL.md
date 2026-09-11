---
name: pre-deploy
description: Gate finale prima di pubblicare online o caricare su GitHub. Riusa solo un audit completo valido dello stesso contenuto, esegue controlli extra e lascia il gate bloccato finché non sono completati.
---

# Pre-Deploy

Completa il controllo finale della pubblicazione, spiegando gli esiti in italiano semplice. Lavora dalla radice del repository che verrà pubblicato. Non usare il pass di un altro progetto e non interpretare direttamente il JSON con regole alternative a quelle dello script.

## Procedura

### 1. Audit completo valido

Controlla se puoi riusare un audit completo con:

```bash
python3 "${CLAUDE_SKILL_DIR}/../../scripts/gate.py" --check
```

Solo exit code zero autorizza il riuso. Il controllo richiede meno di 30 minuti **e** identità invariata del repository e dei contenuti. Il solo HEAD uguale o un timestamp recente non bastano. Se cambia lo stack, il database advisory o una configurazione remota rilevante, oppure il report precedente ha lacune, richiedi comunque nuova verifica: la cache locale non prova lo stato di sistemi esterni.

Se non è valido, esegui `security-audit` completo. Un audit parziale o incompleto non basta. Se fallisce, interrompi la pubblicazione e lascia il gate fail/incomplete; non procedere verso un pass con conteggi inventati.

### 2. Invalida durante i controlli extra

Prima degli extra sospendi il pass preservando l’identità e la scadenza dell’audit appena validato:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" begin --reuse
```

Procedi solo se il comando riesce. Non usare un nuovo `begin` per rinnovare la scadenza di un audit riusato. Da qui un’interruzione lascia il gate incompleto.

Verifica:

1. **File sensibili**: `.env` e credenziali locali correttamente ignorati e non tracciati. Controlla Git e la destinazione effettiva; non assumere che `.gitignore` rimuova file già tracciati.
2. **Contenuto pubblicato**: cartella di output e regole di inclusione non devono pubblicare `.env`, `.git`, dump o backup sensibili. Esamina il risultato della build, non solo i sorgenti.
3. **Variabili in produzione**: verifica o indica le variabili necessarie sulla piattaforma, senza mostrarne i valori. Se una configurazione necessaria alla sicurezza non può essere verificata, registra la lacuna e lascia incomplete.
4. **Build**: esegui il comando di build del progetto, se pertinente, e controlla esito e output pubblicato. Build fallita o non verificabile non autorizza pass.
5. **Destinazione**: conferma dalla richiesta quale repository/piattaforma e quale visibilità sono voluti. Chiedi solo scelte non già espresse che richiedono l’utente.

Se la build o altri passaggi cambiano contenuti coperti dallo snapshot, ripeti l’audit completo sullo stato risultante; non catturare semplicemente uno snapshot nuovo per convalidare modifiche mai esaminate.

### 3. Esito

Solo dopo audit completo valido, extra completati, copertura completa e zero critici/alti/medi:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" pass 0 0 0 <bassi> --scope full --complete
python3 "${CLAUDE_SKILL_DIR}/../../scripts/gate.py" --check
```

Entrambi i comandi devono riuscire. Il riuso non prolunga i 30 minuti dell’audit originario. Comunica il via libera riferito ai contenuti controllati e alla finestra residua, senza garantire sicurezza assoluta; ricorda eventuali variabili da configurare.

Con problemi bloccanti, scrivi immediatamente:

```bash
bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" fail <critici> <alti> <medi> <bassi>
```

Con controllo mancante, interrotto, errore o contenuti cambiati, scrivi invece `incomplete` con i conteggi noti. Zero finding noti non significa controllo completo. Aggiorna il report con extra effettuati, errori e lacune. Spiega il blocco concreto e, se pertinente, indica `fix-security` seguito da nuovo pre-deploy.

## Regole

- Mai scrivere pass per fretta, azzeramento manuale dei conteggi o vecchia approvazione. Gli esiti incerti medi o superiori bloccano.
- Non usare `VIBE_SHIELD_SKIP=1` di iniziativa. Se l’utente insiste, spiega il rischio concreto e la possibilità di scelta consapevole senza descriverla come un controllo superato.
- Non mostrare valori di segreti. Gli hook dipendono dall’host e dai comandi intercettati: controlla che siano effettivamente attivi, senza dedurlo dalla sola disponibilità della skill.
