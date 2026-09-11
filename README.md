# 🛡️ Vibe Shield

**Beta sperimentale — versione 0.5.1-beta.2.** Software gratuito con [licenza MIT](LICENSE); l’uso dei modelli AI può avere costi o consumare il tuo abbonamento.

Versione 0.5.1-beta.2: gate basato sui contenuti e audit con meno analisi duplicate. I vecchi pass 0.4.x non sono riutilizzabili: serve un nuovo audit.

Plugin per assistere i controlli di sicurezza durante lo sviluppo e prima della pubblicazione. Combina scanner, revisione AI e blocchi nei comandi intercettati dall’host, con spiegazioni in italiano semplice. Non è una certificazione di sicurezza né una piattaforma completa di cybersecurity.

## Cosa fa

Tre livelli di controllo nelle sessioni in cui l’host carica ed esegue gli hook:

1. **Mentre lavori**: se Claude scrive una chiave API o una password vera in un file, l’hook può segnalare il problema; la bonifica richiede poi l’intervento dell’assistente.
2. **Al commit**: prima dei `git commit` intercettati viene controllato il contenuto destinato al commit. Se contengono segreti o file sensibili (`.env`, chiavi private, credenziali), il commit viene bloccato con le istruzioni per sistemare.
3. **Alla pubblicazione**: `git push` e i comandi di deploy (Vercel, Netlify, Firebase, Wrangler, Fly, Railway, npm publish, gh repo create) vengono bloccati finché un audit di sicurezza non risulta completo e superato da meno di 30 minuti **e** riferito alla stessa identità del repository e dei contenuti. L'audit passa solo con zero problemi critici, alti E medi.

## Comandi (skill)

| Comando | Cosa fa |
| --- | --- |
| `/security-audit` | Scanner prima dell’AI, revisione semantica e specialisti quando servono. Verifica indipendente dei problemi medi o superiori per piccoli gruppi correlati. Report con copertura esplicita; gli audit parziali non sbloccano il gate. |
| `/pre-deploy` | Il via libera alla pubblicazione: audit più controlli specifici da deploy. Apre il blocco su push e deploy. |
| `/fix-security` | Corregge i problemi trovati: applica da solo i fix sicuri, spiega quelli che richiedono una tua decisione. |
| `/secrets-scan` | Ricerca e bonifica guidata di chiavi e password esposte, anche nella storia git. |
| `/setup-security` | Blindatura preventiva di un progetto nuovo: .gitignore, .env, security header, difese per lo stack usato. |
| `/security-help` | Spiega in parole semplici blocchi, termini e funzionamento della protezione. |
| `/second-opinion` | OPZIONALE, spento di default: sottopone i problemi trovati anche a modelli AI di altri provider installati sul computer (Gemini CLI, Codex CLI, Ollama per open source locali) e confronta i verdetti. Parte solo se lo chiedi tu. |
| `/post-deploy-check` | Controlla il sito GIÀ online, dall'esterno, come lo vedrebbe un bot: header di sicurezza, file sensibili raggiungibili (.env, .git), sourcemap, cookie, pagine d'errore. Solo su siti tuoi, con richieste passive. |
| `/incident-response` | Guida di emergenza se il danno è già fatto: chiave pubblicata, addebiti anomali, sito compromesso. Prima si revoca e si contiene, poi si indaga, poi si sistema. |

I comandi sono namespaced dal plugin: se il nome corto non risponde, usa la forma `/vibe-shield:security-audit`.

## Agenti inclusi

| Agente | Specialità |
| --- | --- |
| `secret-scanner` | Chiavi API, password, token, file sensibili, storia git |
| `code-auditor` | Vulnerabilità nel codice: injection, XSS, autorizzazioni rotte, IDOR, SSRF, upload, crittografia debole |
| `dependency-auditor` | Dipendenze vulnerabili, pacchetti sospetti, typosquatting |
| `config-auditor` | CORS, security header, cookie, debug in produzione, RLS Supabase, regole Firebase, Docker, CI/CD |
| `finding-verifier` | Verifica avversariale: riceve ogni problema trovato e cerca di smentirlo leggendo il codice reale; conferma solo ciò che regge |

## Modelli usati

Gli agenti ereditano il modello configurato nella sessione; il plugin non impone un modello più costoso. Un modello esplicitamente richiesto per l’audit viene passato come override, se supportato dall’host. La scelta del modello non dimostra da sola la qualità dell’audit.

### Come limita il consumo di token

- Ricognizione unica e scanner deterministici prima della revisione AI; nel contesto entrano risultati sintetici.
- Specialisti attivati per compiti utili, senza quattro agenti obbligatori per ogni progetto.
- Verificatore indipendente per gruppi di uno–quattro problemi correlati, con un verdetto per ciascuno.
- Pre-deploy riusa un audit completo valido dello stesso contenuto entro la finestra di 30 minuti. Un cambio dei contenuti richiede una nuova valutazione completa.

Questi interventi riducono il lavoro duplicato; il risparmio non è ancora misurato. Il report registra copertura e deleghe; durata e token solo quando l’host li fornisce. Scanner indisponibili, database irraggiungibili o budget esaurito producono un controllo incompleto, mai un’approvazione. L’analisi selettiva delle modifiche non autorizza l’intero progetto.

### Secondo parere di altri provider (opzionale, spento di default)

Gli agenti usano il modello della sessione compatibile con l’host. In più, se sul computer hai installato i CLI di altri provider, puoi chiedere un secondo parere esterno con `/second-opinion` (o dicendo ad esempio "chiedi anche a Gemini"):

- **Gemini CLI** (Google) e **Codex CLI** (OpenAI): revisori cloud. Prima dell'invio ti viene chiesto il consenso, perché estratti del tuo codice vanno anche ai loro server.
- **Ollama**: modelli open source in locale, il codice non lascia il computer, nessun consenso necessario.

I pareri esterni sono consultivi: aumentano la fiducia nel risultato ma non cambiano il gate di pubblicazione, che resta quello dell'audit Vibe Shield. Nei prompt inviati all'esterno i segreti vengono sempre mascherati prima dell'invio.

## Installazione

Per provare questa beta scarica **Source code (zip)** dalla [prerelease v0.5.1-beta.2](https://github.com/mdigital94/vibe-shield-plugin/releases/tag/v0.5.1-beta.2), estrailo e usa l’installazione da cartella locale qui sotto. Il ramo principale può contenere una versione precedente.

Dal ramo principale di GitHub:

```
/plugin marketplace add mdigital94/vibe-shield-plugin
/plugin install vibe-shield@vibe-shield-marketplace
```

Da cartella locale:

```
/plugin marketplace add /percorso/di/questa/cartella
/plugin install vibe-shield@vibe-shield-marketplace
```

Per sviluppo e test del plugin stesso:

```
claude --plugin-dir /percorso/di/questa/cartella
```

Dopo l’installazione riavvia la sessione e prova `/vibe-shield:security-help`. Prima di affidarti ai blocchi, esegui le prove di attivazione in [TESTING.md](TESTING.md) su un repository temporaneo: la risposta di una skill non prova che gli hook siano attivi.

Primo passo consigliato su ogni progetto: esegui `/setup-security`.

## Come si sblocca un blocco

- **Commit bloccato**: segui le istruzioni mostrate (spostare i segreti in `.env`, togliere i file sensibili dallo stage), poi ripeti il commit. Per la bonifica guidata: `/secrets-scan`.
- **Push o deploy bloccato**: esegui `/pre-deploy`. Se l'audit passa, puoi pubblicare entro 30 minuti, solo finché identità e contenuti controllati restano invariati. Un errore nei controlli extra invalida il pass precedente.
- **Emergenza consapevole**: la variabile d'ambiente `VIBE_SHIELD_SKIP=1` disattiva i blocchi per un singolo comando. Usala solo sapendo cosa stai facendo: i blocchi esistono per proteggerti.

## File di lavoro

Il plugin scrive nel progetto una cartella `.vibe-shield/` (da escludere tramite `.gitignore`, come previsto da `/setup-security`):

- `report.md`: l'ultimo report di audit completo.
- `status.json`: il gate che sblocca push e deploy (esito, copertura, data, identità del repository e dei contenuti, conteggio problemi). È uno stato locale, non una firma o una prova contro manomissioni da parte di chi può scrivere sul filesystem.
- `allowlist` (opzionale, lo crei tu o Claude su tua richiesta): un'espressione regolare per riga, applicata ai controlli commit e allo scanner guidato. Il controllo finale di pubblicazione è conservativo e non applica queste eccezioni. Righe che iniziano con `#` sono commenti. Da usare con giudizio: serve per i falsi positivi ricorrenti, non per zittire problemi veri.

## Protezione anche fuori da Claude Code

Gli hook operano solo sui tool e comandi intercettati dall’host. La presenza delle skill in Codex o in un altro host non dimostra che gli hook Claude Code vengano eseguiti: va collaudata nell’host reale. Terminali esterni, alias, script intermedi e tool non intercettati possono restare fuori dal controllo. Per coprire modifiche fatte da editor, dal sito di GitHub o da altri collaboratori, `/setup-security` installa nel progetto anche:

- `.github/workflows/security.yml`: scansione segreti (gitleaks) e vulnerabilità delle dipendenze a ogni push e ogni lunedì.
- `.github/dependabot.yml`: aggiornamenti di sicurezza automatici delle dipendenze.

## Audit periodico (consigliato per progetti online da tempo)

Le dipendenze diventano vulnerabili col passare del tempo anche se il codice non cambia. Oltre al cron settimanale già incluso nel workflow CI, puoi programmare un audit completo ricorrente in Claude Code (es. una routine settimanale che esegue `/security-audit` sul progetto) oppure lanciarlo a mano ogni tanto: un progetto pubblicato e dimenticato è il bersaglio preferito dei bot.

## Requisiti e note

- Runtime richiesto: macOS/Linux, Bash, Git, grep e **Python 3.8 o successivo** per parsing dei comandi, snapshot e gate. Gli scanner di vulnerabilità dei singoli stack devono essere disponibili per completare le rispettive aree di audit.
- Uno scanner a pattern non trova ogni segreto. La revisione AI può mancare vulnerabilità o produrre falsi allarmi: servono prove, test e copertura esplicita.
- Il dispatcher accetta comandi diretti supportati; comandi composti (anche `git add && git commit`), opzioni globali Git ambigue e destinazioni di deploy esplicite non supportate vengono bloccati con una spiegazione. Esegui add, commit e pubblicazione separatamente. La presenza di un comando fra quelli riconosciuti non implica supporto per tutte le sue opzioni.
- Il gate automatico richiede un repository Git con storia completa; deploy senza Git, clone shallow e submodule richiedono una verifica separata e non ricevono un pass automatico di pubblicazione. La storia viene controllata conservativamente su tutti i riferimenti locali, non soltanto sui commit diretti al remoto: può bloccare anche segreti in branch che non stai inviando.
- Lo snapshot include file tracciati, stage, riferimenti Git, regole del plugin e file locali ignorati, compresi gli output di build. Esclude i report interni e alcune directory di dipendenze/cache non tracciate. La scansione automatica dei segreti alla pubblicazione copre storia e file non ignorati; i contenuti della cartella distribuita e i servizi remoti richiedono i controlli di `/pre-deploy`.
- Il gate richiede età inferiore a 30 minuti **e** identità invariata. Include lo stato del codice considerato dal gate; non attesta automaticamente servizi remoti, impostazioni nel cloud o database advisory mutati dopo la scansione.
- I blocchi locali non sono una barriera contro un utente che controlla la macchina. CI, permessi e controlli del provider completano la protezione; verificare la copertura del template CI per gli stack effettivamente usati.
- Le regressioni automatiche verificano casi dei guard, non misurano ancora tasso di vulnerabilità mancate, falsi positivi o qualità complessiva dell’audit. Non è dimostrato un livello di sicurezza “massimo”.

Per le regressioni locali: `python3 -m unittest discover -s tests`. Per il collaudo nell’host e il confronto dei consumi vedi [TESTING.md](TESTING.md).

## Struttura del repo

```
.claude-plugin/    plugin.json + marketplace.json
skills/            le 9 skill (comandi)
agents/            i 5 agenti specializzati (4 auditor + verificatore avversariale)
hooks/hooks.json   hook automatici (PreToolUse su Bash, PostToolUse su Write/Edit)
scripts/           script di guardia e scansione (Bash + Python 3)
templates/         workflow CI GitHub Actions e dependabot, installati da /setup-security
```

## Stato della beta e contributi

La precedente candidata 0.5.1-beta.1 ha superato 55 regressioni e la CI su Linux/macOS con Python 3.9/3.12, inclusa la scansione Gitleaks della storia. In una nuova sessione Claude su un progetto temporaneo, il plugin scaricato da GitHub ha consentito una lettura Git e bloccato automaticamente sia un commit con credenziale sintetica sia un push senza audit. È una prova locale con caricamento tramite `--plugin-dir`, non un’installazione da parte di un tester esterno.

La 0.5.1-beta.2 aggiunge la pubblicazione controllata delle prerelease GitHub da tag verificato. L’esito della sua suite e della CI va verificato sul commit della release. Queste prove non misurano la capacità di trovare vulnerabilità nelle applicazioni.

Restano da completare l’installazione da parte di un tester esterno e prove su applicazioni con vulnerabilità note. Non viene dichiarata una copertura certificata di uno stack applicativo. Windows e host diversi da Claude Code non sono collaudati end-to-end.

Per contribuire vedi [CONTRIBUTING.md](CONTRIBUTING.md), per le novità [CHANGELOG.md](CHANGELOG.md). Segnala problemi ordinari nelle [issue](https://github.com/mdigital94/vibe-shield-plugin/issues); per vulnerabilità del plugin segui [SECURITY.md](SECURITY.md). Non caricare log integrali, credenziali o codice privato.

### Candidata 0.5.1-beta.2

La candidata include il controllo dei tag annotati inviati tramite identificatore esplicito, la scansione dei riferimenti Git a tree/blob (compresi checkpoint locali) e l’invalidazione del pass quando cambia codice applicativo dentro `.vibe-shield/`. Le misurazioni private delle esecuzioni reali distinguono input, scrittura/lettura cache e output: non costituiscono un confronto controllato del risparmio tra versioni.
