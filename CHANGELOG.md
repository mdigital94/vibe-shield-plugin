# Changelog

## 0.5.1-beta.2 — prerelease

- Supporto ristretto alle prerelease GitHub da tag locale/remoto verificato sul contenuto approvato, senza allegati.
- Documentata la prova degli hook reali in una sessione Claude separata sulla candidata beta.1.
- Distinte le istruzioni per scaricare la beta da quelle del ramo principale.
- CI della beta.1 superata; collaudo umano esterno e confronto controllato dei consumi ancora da raccogliere.

## 0.5.1-beta.1 — candidata

- Corretta scansione dei metadati dei tag annotati inviati con identificatore esplicito.
- Supportati riferimenti locali tree/blob, inclusi checkpoint Codex; i contenuti vengono scansionati, i submodule restano incompleti.
- Approvazione invalidata anche da cambiamenti a codice applicativo in `.vibe-shield/`.
- Preparati licenza MIT, policy di segnalazione, issue template e CI multipiattaforma.
- Rimossa email non necessaria dai metadati correnti del marketplace, senza riscrivere la storia pubblica.


## 0.5.0 — beta, preparazione al rilascio

### Affidabilità

- Approvazione legata al repository e ai contenuti, con validità inferiore a 30 minuti; le approvazioni 0.4.x non sono riutilizzabili.
- Audit parziali, falliti o incompleti lasciano bloccata la pubblicazione; pre-deploy conserva la scadenza originale quando riusa un audit.
- Controlli sul contenuto destinato al commit e sugli oggetti della storia Git; gestione conservativa di comandi composti, repository differenti e configurazioni non supportate.
- Suite di 46 regressioni per i comportamenti verificati dei guard e del template CI.

### Audit e consumi

- Scanner prima dell’analisi AI, specialisti attivati secondo necessità e verifica indipendente per piccoli gruppi di problemi correlati.
- Modello ereditato dalla sessione, senza imposizione del modello più costoso.
- Risparmio di token non ancora dimostrato con un confronto controllato; nessuna percentuale promessa.

### Preparazione della distribuzione

- Licenza MIT, istruzioni e limiti della beta, policy di sicurezza, guida ai contributi e modelli di issue.
- Workflow di regressione Linux/macOS e scansione segreti, con azioni fissate a commit e permessi di sola lettura.

Il canale di segnalazione privata è stato abilitato e verificato il 2026-09-11. L’esecuzione del workflow su GitHub e l’installazione da parte di un tester esterno devono ancora essere verificate prima di promuovere la candidata. Questa voce documenta le modifiche preparate e non attesta una pubblicazione avvenuta.
