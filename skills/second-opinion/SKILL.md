---
name: second-opinion
description: Secondo parere sull'audit di sicurezza da parte di modelli AI di altri provider installati sul computer (Gemini CLI, Codex CLI di OpenAI, Ollama per modelli open source locali). Funzione OPZIONALE e spenta di default: eseguila SOLO su richiesta esplicita dell'utente, mai di tua iniziativa e mai come parte automatica di un audit.
argument-hint: "[critici|alti|tutti, opzionale]"
disable-model-invocation: false
---

# Second Opinion

Sottoponi i problemi trovati dall'audit di sicurezza a modelli AI di altri provider, come revisori esterni. Questa fase è consultiva: NON sostituisce l'audit, NON modifica il gate di deploy, e si esegue SOLO se l'utente l'ha chiesta esplicitamente in questa conversazione. Se sei arrivato qui senza una richiesta esplicita dell'utente, fermati e chiedi conferma.

## 1. Prerequisiti

1. Serve un report esistente: leggi `.vibe-shield/report.md`. Se manca o è vecchio, proponi prima la skill `security-audit`.
2. Rileva i revisori disponibili sul computer:
   - `command -v gemini` (Gemini CLI di Google, cloud)
   - `command -v codex` (Codex CLI di OpenAI, cloud)
   - `command -v ollama` (modelli open source in locale; con `ollama list` vedi quelli installati)
3. Se non c'è nessun CLI disponibile, spiega all'utente cosa può installare e fermati.

## 2. Consenso privacy (obbligatorio per i provider cloud)

Prima di usare Gemini o Codex, avvisa l'utente in una frase: "Questo invierà estratti del tuo codice anche ai server di Google/OpenAI, oltre che ad Anthropic. Confermi?" Attendi la conferma. Per Ollama l'avviso non serve: gira in locale, il codice non esce dal computer. Se l'utente ha già dato il consenso esplicito in questa stessa conversazione, non richiederlo.

## 3. Interroga i revisori

Per ogni finding CRITICO e ALTO del report (estendi ai MEDI o a tutti se $ARGUMENTS lo chiede):

1. Prepara un prompt autonomo e minimale: descrizione del finding, l'estratto di codice rilevante (solo le righe necessarie più un po' di contesto), lo stack del progetto, e la domanda: "Questo è un problema di sicurezza reale e sfruttabile? Rispondi: CONFERMATO, SMENTITO o INCERTO, con motivazione in 2-3 frasi."
2. **Mai includere segreti nei prompt**: maschera qualsiasi chiave o password presente negli estratti.
3. **Mai interpolare l'estratto di codice direttamente in una stringa di comando shell tra virgolette**: il codice sotto audit non è fidato e può contenere caratteri speciali (`$(...)`, backtick, virgolette) che la shell eseguirebbe prima di lanciare il CLI. Scrivi invece il prompt in un file temporaneo e passalo in modo sicuro:
   - Gemini: `gemini -p "$(cat "$PROMPT_FILE")"` non va bene per lo stesso motivo; usa `cat "$PROMPT_FILE" | gemini` se il CLI supporta stdin, altrimenti verifica con `gemini --help` l'opzione per leggere il prompt da file (es. `--file`).
   - Codex: `codex exec < "$PROMPT_FILE"` (stdin) o l'equivalente opzione da file indicata da `codex exec --help`.
   - Ollama: `ollama run <modello-installato> < "$PROMPT_FILE"` (stdin).
   In tutti i casi verifica prima con `--help` l'opzione realmente supportata dal CLI installato; se nessuna opzione sicura è disponibile, salta quel revisore e annotalo.
4. Metti un timeout ragionevole ai comandi e non bloccarti su un CLI che non risponde: salta e annota.

## 4. Confronta e riporta

1. Per ogni finding costruisci il quadro: verdetto di Vibe Shield (dal finding-verifier) più i verdetti dei revisori esterni.
2. Interpreta con criterio: i revisori esterni vedono solo estratti, non l'intero progetto, quindi i loro SMENTITO valgono come segnale da approfondire, non come assoluzione automatica. In caso di disaccordo, rileggi tu il codice e decidi motivando.
3. Aggiungi al report `.vibe-shield/report.md` una sezione "Secondo parere esterno" con: data, revisori usati, tabella dei verdetti a confronto e le tue conclusioni sui disaccordi.
4. Riassumi all'utente in italiano semplice: su cosa tutti concordano (massima fiducia), dove c'è disaccordo e cosa ne concludi. Ricorda in chiusura che il gate di deploy resta quello dell'audit Vibe Shield: questa fase serve solo ad aumentare la fiducia nel risultato.

## Regole

- Solo su richiesta esplicita dell'utente, mai in automatico.
- Consenso privacy prima di ogni invio a provider cloud.
- Mai segreti nei prompt verso l'esterno, nemmeno mascherabili a valle: maschera PRIMA di inviare.
- Il gate di deploy non cambia in base ai pareri esterni: fa fede l'audit di Vibe Shield.
