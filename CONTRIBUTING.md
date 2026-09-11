# Contribuire a Vibe Shield

La beta cerca riproduzioni minime, correzioni dei guard, miglioramenti alla chiarezza e prove sui consumi. Prima di proporre una funzionalità ampia, descrivi nelle issue il problema concreto e il risultato atteso.

Per le vulnerabilità segui [SECURITY.md](SECURITY.md). Nelle issue ordinarie indica versione del plugin/host, sistema operativo, passi, risultato atteso e osservato. Usa repository temporanei e credenziali sintetiche; rimuovi percorsi personali, log privati e dati di clienti.

## Modifiche e verifiche

1. Mantieni ogni modifica limitata al problema affrontato e aggiorna la documentazione correlata.
2. Per un difetto funzionale aggiungi un test che riproduca il comportamento errato e verifichi la correzione. I test non devono pubblicare né accedere a credenziali reali.
3. Esegui `python3 -m unittest discover -s tests` dalla radice del repository (Bash, Git e Python 3.8+ richiesti).
4. Se tocchi gli hook o l’installazione, segui anche [TESTING.md](TESTING.md) e distingui test diretti degli script da esecuzione automatica nell’host.
5. Nella pull request descrivi problema, cambiamento, verifiche eseguite e limiti ancora aperti. Non dichiarare test non eseguiti.

Il runtime Python usa la libreria standard. Il workflow del plugin verifica regressioni e segreti; il template in `templates/` è invece destinato ai progetti degli utenti e va adattato alle loro dipendenze. I risultati AI dipendono dal modello e non sono coperti dalla sola suite dei guard.

I contributi sono distribuiti con la [licenza MIT](LICENSE) del repository.
