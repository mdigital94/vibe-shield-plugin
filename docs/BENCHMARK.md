# Prove della beta 0.6

Questi risultati riguardano piccoli progetti sintetici e non certificano la sicurezza delle applicazioni. Il banco contiene 30 casi: 12 coppie vulnerabile/corretto, 2 casi scanner e 4 tentativi di manipolare il revisore. Le risposte attese restano fuori dai file inviati al modello.

## Cosa è stato osservato

Il primo tentativo con Claude CLI e `fable` (restituito come `claude-fable-5-1`) ha prodotto 27 report su 28 revisioni; un caso è stato rifiutato due volte. I report riusciti dichiarano 286.035 token, includendo input, output, lettura e scrittura della cache. I consumi dei tentativi falliti non sono disponibili: il totale effettivo è quindi incompleto. I token non misurano euro né percentuale della quota dell'abbonamento.

Una lettura assistita dall'AI, non una revisione umana indipendente, ha individuato 14 report originali che iniziavano a metà frase. Altri due casi avevano parte dell'evidenza nascosta dal mascheramento. Non pubblichiamo precision o recall del vecchio tentativo: attribuire quelle omissioni al modello sarebbe fuorviante.

La raccolta dello stream è stata corretta. Tre casi sono stati ripetuti senza aumentare il limite di output: tutti hanno prodotto report completi; uno conteneva due blocchi ricomposti. Il nuovo mascheramento mantiene le espressioni Python rilevanti, nascondendo i valori letterali sensibili. Non preserva allo stesso modo tutti i linguaggi; nei formati ambigui rimane conservativo.

## Confronto esplorativo della risposta concisa

Campione stabilito prima dell'esecuzione: c01/c02 (SQL), c13/c14 (HTML), c21 (password nel log), c29 (log e istruzione di lettura non autorizzata). Ogni caso viene eseguito una volta per condizione, dettagliata e concisa, alternandone l'ordine. Stesso sorgente, mascheramento, modello, accesso Claude, limite di output 2000 per risposta e timeout 180 secondi. Massimo 12 chiamate; nessun retry automatico.

I report sono valutati rispetto alla rubrica del caso, distinguendo finding dimostrati, ipotesi e hardening opzionale. Una sola ripetizione non stima la variabilità e non dimostra significatività statistica, equivalenza di qualità o un risparmio generalizzabile. La cache può cambiare tra richieste. I risultati sono una misura esplorativa della coorte finale sotto riportata.


### Risultati del campione finale

| Misura (6 casi per formato) | Dettagliata | Concisa |
| --- | ---: | ---: |
| Token output | 8250 | 5243 |
| Token input fuori cache | 12 | 12 |
| Token letti dalla cache | 3654 | 3654 |
| Token scritti nella cache | 20999 | 21089 |
| Somma delle categorie token | 32915 | 29998 |
| Secondi complessivi delle chiamate | 149.778 | 106.131 |

Differenza osservata: 36.4% di output in meno e 8.9% in meno nella somma delle categorie token. Non è una promessa di risparmio: una sola ripetizione, latenza e cache variabili, nessuna inferenza statistica.

Durante la verifica quattro risposte sul logging sono state escluse dalla valutazione e ripetute perché il mascheramento dei report cancellava evidenza; la condizione c29 concisa ha richiesto una seconda ripetizione per una diversa ambiguità di virgolette. La coorte finale usa gli otto report iniziali sui primi quattro casi e gli ultimi quattro report utilizzabili sui due casi di logging. Le impostazioni di generazione sono rimaste uguali; è cambiato il trattamento locale del testo restituito. I risultati originali sono stati conservati, non sostituiti silenziosamente.

L'intero esperimento ha richiesto **17 chiamate e 88923 token dichiarati**, incluse le risposte scartate. Le dodici risposte della coorte finale sono solo la base del confronto; non rappresentano tutto il consumo sostenuto.

La lettura assistita della coorte finale ha riconosciuto gli stessi quattro problemi attesi in entrambi i formati e giudizi coerenti sui due casi corretti. Non è una revisione umana cieca: non dimostra assenza di falsi positivi, equivalenza generale o copertura oltre questi esempi.

## Riprodurre

Il metodo e i comandi sono in [benchmarks/README.md](../benchmarks/README.md). Le opzioni `--detail concise` e `--detail detailed` selezionano le condizioni; usare cartelle risultati diverse. Annotazioni umane e verifica indipendente restano necessarie prima di usare precision/recall come evidenza di qualità.

La suite automatica verifica anche segreti, gate, fallimenti dei provider, limiti del processo, integrità dei file e parsing delle continuazioni. I test passati attestano quei comportamenti, non il riconoscimento di tutte le vulnerabilità.
