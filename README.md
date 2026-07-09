# 🛡️ Vibe Shield

Plugin di Claude Code che blinda automaticamente qualsiasi progetto prima che finisca online o su GitHub: dal vibe coding allo sviluppo professionale. Controlla, blocca e corregge, spiegando tutto in italiano semplice, comprensibile anche a chi non ha competenze tecniche.

## Cosa fa

Tre livelli di protezione, sempre attivi dopo l'installazione:

1. **Mentre lavori**: se Claude scrive una chiave API o una password vera in un file, scatta subito un avviso e il problema viene corretto (segreto spostato in `.env`).
2. **Al commit**: prima di ogni `git commit` i file vengono scansionati. Se contengono segreti o file sensibili (`.env`, chiavi private, credenziali), il commit viene bloccato con le istruzioni per sistemare.
3. **Alla pubblicazione**: `git push` e i comandi di deploy (Vercel, Netlify, Firebase, Wrangler, Fly, Railway, npm publish, gh repo create) vengono bloccati finché un audit di sicurezza completo non risulta superato da meno di 30 minuti (o sullo stesso commit). L'audit passa solo con zero problemi critici, alti E medi.

## Comandi (skill)

| Comando | Cosa fa |
| --- | --- |
| `/security-audit` | Audit completo con 4 agenti in parallelo (segreti, codice OWASP Top 10, dipendenze, configurazioni) più verifica incrociata: ogni problema trovato viene ricontrollato da un agente indipendente che cerca di smentirlo. Report in italiano semplice. |
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

Gli agenti di audit NON usano il modello della sessione: sono configurati sul modello migliore disponibile (campo `model: fable` nel frontmatter di ogni file in `agents/`). Questo garantisce che le verifiche di sicurezza girino sempre al massimo livello, anche se nella sessione stai usando un modello più veloce.

- **Cambiare modello per sempre**: modifica il campo `model:` nei file `agents/*.md` (valori: `fable`, `opus`, `sonnet`, `haiku` o un ID modello completo).
- **Cambiare modello per un singolo audit**: chiedilo e basta, ad esempio "fai l'audit con Opus": la skill passa l'override agli agenti.
- **Se il modello configurato non è disponibile** per il tuo account, gli agenti vengono rilanciati con il modello della sessione e la cosa ti viene segnalata.

### Secondo parere di altri provider (opzionale, spento di default)

Gli agenti del plugin girano su modelli Claude (è un plugin di Claude Code). In più, se sul computer hai installato i CLI di altri provider, puoi chiedere un secondo parere esterno con `/second-opinion` (o dicendo ad esempio "chiedi anche a Gemini"):

- **Gemini CLI** (Google) e **Codex CLI** (OpenAI): revisori cloud. Prima dell'invio ti viene chiesto il consenso, perché estratti del tuo codice vanno anche ai loro server.
- **Ollama**: modelli open source in locale, il codice non lascia il computer, nessun consenso necessario.

I pareri esterni sono consultivi: aumentano la fiducia nel risultato ma non cambiano il gate di pubblicazione, che resta quello dell'audit Vibe Shield. Nei prompt inviati all'esterno i segreti vengono sempre mascherati prima dell'invio.

## Installazione

Da GitHub (dopo aver pubblicato questo repo):

```
/plugin marketplace add <owner>/<repo>
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

Primo passo consigliato su ogni progetto: esegui `/setup-security`.

## Come si sblocca un blocco

- **Commit bloccato**: segui le istruzioni mostrate (spostare i segreti in `.env`, togliere i file sensibili dallo stage), poi ripeti il commit. Per la bonifica guidata: `/secrets-scan`.
- **Push o deploy bloccato**: esegui `/pre-deploy`. Se l'audit passa, hai 30 minuti (o lo stesso commit) per pubblicare.
- **Emergenza consapevole**: la variabile d'ambiente `VIBE_SHIELD_SKIP=1` disattiva i blocchi per un singolo comando. Usala solo sapendo cosa stai facendo: i blocchi esistono per proteggerti.

## File di lavoro

Il plugin scrive nel progetto una cartella `.vibe-shield/` (auto aggiunta al `.gitignore`):

- `report.md`: l'ultimo report di audit completo.
- `status.json`: il gate che sblocca push e deploy (`result`, commit, data, conteggio problemi).
- `allowlist` (opzionale, lo crei tu o Claude su tua richiesta): un'espressione regolare per riga; i match che corrispondono vengono considerati falsi allarmi accettati e non bloccano più. Righe che iniziano con `#` sono commenti. Da usare con giudizio: serve per i falsi positivi ricorrenti, non per zittire problemi veri.

## Protezione anche fuori da Claude Code

Gli hook proteggono solo ciò che passa da Claude Code. Per coprire modifiche fatte da editor, dal sito di GitHub o da altri collaboratori, `/setup-security` installa nel progetto anche:

- `.github/workflows/security.yml`: scansione segreti (gitleaks) e vulnerabilità delle dipendenze a ogni push e ogni lunedì.
- `.github/dependabot.yml`: aggiornamenti di sicurezza automatici delle dipendenze.

## Audit periodico (consigliato per progetti online da tempo)

Le dipendenze diventano vulnerabili col passare del tempo anche se il codice non cambia. Oltre al cron settimanale già incluso nel workflow CI, puoi programmare un audit completo ricorrente in Claude Code (es. una routine settimanale che esegue `/security-audit` sul progetto) oppure lanciarlo a mano ogni tanto: un progetto pubblicato e dimenticato è il bersaglio preferito dei bot.

## Requisiti e note

- Funziona su macOS e Linux. Gli script usano solo bash, git e grep; per leggere il JSON degli hook usano il primo disponibile tra `jq`, `python3` e `node` (su un sistema con Claude Code almeno uno c'è sempre).
- Se sono installati strumenti dedicati (`gitleaks`, `pip-audit`, ecc.) il plugin li sfrutta, ma non sono richiesti.
- **Onestà sul rischio**: Vibe Shield riduce drasticamente la probabilità di incidenti, non la azzera. Nessuno strumento può garantire sicurezza assoluta.

## Struttura del repo

```
.claude-plugin/    plugin.json + marketplace.json
skills/            le 9 skill (comandi)
agents/            i 5 agenti specializzati (4 auditor + verificatore avversariale)
hooks/hooks.json   hook automatici (PreToolUse su Bash, PostToolUse su Write/Edit)
scripts/           script di guardia e scansione (bash puro, nessuna dipendenza)
templates/         workflow CI GitHub Actions e dependabot, installati da /setup-security
```
