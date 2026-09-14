# CLI indipendente: provider e modello

Stato: beta **0.6.0b1**, sorgente al tag GitHub `v0.6.0-beta.1`. Non pubblicata su PyPI. La CLI offre revisioni consultive; il plugin Claude Code mantiene i propri audit e hook.

## Installazione dal checkout di sviluppo

Richiede Python 3.9+, Git, Bash e grep su macOS/Linux. Consigliato un ambiente virtuale:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/vibe-shield providers
```

Puoi usare anche `python3 -m vibe_shield` dalla radice del checkout. Il pacchetto include gli stessi script/pattern del plugin: non è necessario installare Claude per usare scanner e API.

## Controlli senza AI

```bash
vibe-shield scan /percorso/progetto
vibe-shield scan /percorso/progetto --history
vibe-shield check /percorso/progetto
```

`scan`: exit 0 nessun match, 2 finding, 3 incompleto. `check`: exit 0 solo per un gate completo valido, altrimenti 2. Una scansione pulita non certifica l’applicazione e non crea un pass.

## Scegli accesso, provider e modello

| Modalità | Provider | Accesso | Stato |
| --- | --- | --- | --- |
| API | `openai` | `OPENAI_API_KEY` | Adattatore Chat Completions |
| API | `anthropic` | `ANTHROPIC_API_KEY` | Adattatore Messages |
| API | `gemini` | `GEMINI_API_KEY` | Adattatore generateContent |
| API | `ollama` | Runtime API configurato | Adattatore chat, default loopback |
| API | `openai-compatible` | `VIBE_SHIELD_API_KEY` e `--endpoint` | Protocollo Chat Completions |
| CLI | `claude` | Accesso già configurato nel CLI | Richiede versione con `--safe-mode` e opzioni di isolamento |
| CLI | Codex, Gemini, Ollama | — | Adattatori non disponibili: isolamento completo non verificato |

API e CLI sono scelte separate. Un abbonamento chat non fornisce automaticamente crediti API. Il CLI Claude usa l’accesso configurato, che può essere un abbonamento o una chiave API. Nessuna credenziale viene copiata dal tool. Configura le chiavi nell’ambiente tramite il tuo gestore di segreti, senza inserirle in file del progetto o negli argomenti del comando.

`--model` è obbligatorio e viene trasmesso al provider senza fallback o sostituzioni. Inserisci un identificatore di modello testuale compatibile con l’API scelta e disponibile al tuo account; il tool non mantiene un catalogo universale di modelli. Compatibilità con un protocollo non significa collaudo di ogni servizio/modello. `--endpoint` è ammesso solo per Ollama e OpenAI-compatible: URL base HTTPS, oppure HTTP su loopback; niente credenziali nell’URL, redirect o proxy ereditati dalle API.

Gli adattatori CLI mancanti non sono dichiarati impossibili: serve verificare che non leggano altri file o eseguano strumenti. La sola modalità read-only non limita necessariamente le letture ai file selezionati. Per quei provider usa l’API disponibile.

## Anteprima e invio esplicito

```bash
vibe-shield review /percorso/progetto --mode api --provider openai \
  --model IL_TUO_MODELLO --file src/app.py --file src/auth.py
```

Senza `--execute` mostra solo il manifest dei file: nessuna rete, nessuna invocazione del CLI, nessuna modifica al gate. Seleziona file relativi al progetto, non cartelle. Per effettuare la richiesta aggiungi `--execute` allo stesso comando: autorizza l’invio e gli eventuali costi dell’accesso scelto.

Esempio con CLI già configurato:

```bash
vibe-shield review /percorso/progetto --mode cli --provider claude \
  --model IL_TUO_MODELLO --file src/app.py --execute
```

Esempio con runtime Ollama locale, modello già disponibile:

```bash
vibe-shield review /percorso/progetto --mode api --provider ollama \
  --model IL_TUO_MODELLO --file src/app.py --execute
```

Endpoint compatibile: `--provider openai-compatible --endpoint https://servizio.example/v1`. Il tool aggiunge `/chat/completions`; Ollama aggiunge `/api/chat`. Se scegli un endpoint Ollama remoto, il codice esce dal computer.

## Dati, limiti ed esiti

- Solo i file espliciti entrano nel prompt, massimo32 file/64KiB complessivi di default. `--max-input-bytes` arriva fino a256KiB. Niente troncamento silenzioso.
- File sensibili per nome, directory di credenziali, binari e symlink sono rifiutati. Mascherati formati noti, assegnazioni di credenziali e chiavi API dell’ambiente; non è una garanzia che ogni dato privato sia riconosciuto. Esamina cosa stai autorizzando a inviare.
- Le API non ricevono strumenti; Claude CLI gira in una cartella temporanea con tool, skill, MCP e personalizzazioni disabilitati. Il login resta gestito dal CLI. Non vengono effettuate modifiche suggerite dal modello.
- `--timeout` limita l’inattività socket per le API e la durata totale per il CLI; default60 secondi. `--max-output-tokens` chiede un limite di output al provider (default2000). Nel CLI è un limite per risposta, non un tetto totale: le continuazioni interne di Claude possono superarlo. L'adattatore non aggiunge retry o fallback; restano i comportamenti interni del CLI.
- `review` è **consultivo sui file selezionati**, non un audit completo dello stack. Quando parte invalida il precedente pass e non scrive mai PASS, anche se il modello risponde “nessun problema”. Se i file selezionati cambiano durante la richiesta, risultato incompleto.
- Report JSON: provider, modello richiesto/restituito quando noto, hash dei file, durata misurata, contatori disponibili e testo mascherato. Risposta del modello trattata come dato non fidato. Exit0 indica revisione completata, **non autorizzazione alla pubblicazione**; errori/limiti producono exit3.
- Claude CLI viene letto in `stream-json`: i blocchi testuali completi sono ricomposti nell'ordine ricevuto, usando gli identificatori dei blocchi per duplicati, ritiri e sostituzioni. Il campo finale `result` non viene aggiunto nuovamente. Thinking, messaggi sintetici e output di agenti figli sono esclusi. `response_segments` conta i blocchi conservati; `response_complete` indica la verifica della conclusione, non la completezza dell'audit.
- In caso di timeout, errore o flusso malformato, i blocchi già verificati restano nel report, mascherati, con stato `incomplete` e uscita3. Un blocco ancora in generazione o una riga JSON troncata non viene ricostruito per supposizione. Senza risultato finale i contatori sono sconosciuti. Lo stream grezzo non viene salvato.
- Token mancanti sono null, non zero. OpenAI/Gemini includono i token in cache nell’input; Anthropic li separa. Non sommare indiscriminatamente input e cache. Non vengono stimati euro, quote abbonamento o risparmio tra modelli.

## Verifiche e lavoro restante

Test automatici su trasporto/processi simulati, selezione file, errori e regressioni; pacchetto verificato fuori dal checkout. Primo collaudo live autorizzato con Claude CLI, abbonamento esistente e alias `fable`, restituito come `claude-fable-5-1`. Su macOS l'adattatore conserva anche `USER`, necessario al CLI per recuperare il login dal Portachiavi. Sono ancora da collaudare gli altri provider/modelli e da completare gli adattatori isolati per gli altri CLI.

Il comando audit completo e le integrazioni bloccanti degli altri host richiedono ulteriore orchestrazione della copertura: una singola revisione AI non sostituisce scanner delle dipendenze, verifica indipendente e controlli di pubblicazione.

## Risposte e consumo

`--detail concise` è il default: risultati con prova, posizione e rimedio, più limiti essenziali. `--detail detailed` conserva il formato esteso. La brevità è una richiesta al modello, non un limite rigido: nessun finding viene tagliato per lunghezza. Nella modalità concisa al modello arrivano percorso e testo; gli hash restano nel report locale. Vedi [confronto esplorativo](BENCHMARK.md).

Il mascheramento del sorgente e quello dei report sono distinti. Nel report, codice inline e blocchi di codice vengono trattati separatamente dalla prosa: valori sensibili rimangono oscurati senza cancellare automaticamente il resto del finding. `review_redacted` segnala modifiche al testo; un report privo di testo disponibile viene marcato incompleto. Questa verifica di disponibilità non valuta la correttezza della risposta. Il mascheramento resta euristico e non garantisce rilevamento di ogni segreto.
