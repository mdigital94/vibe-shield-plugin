# Vibe Shield — Guida per i tester

Grazie per il test. Vibe Shield è un plugin per Claude Code che assiste i controlli dei progetti prima della pubblicazione: scansione segreti, audit OWASP con verifica avversariale, blocco automatico di commit e deploy a rischio, fix guidati. Target: anche utenti non tecnici (vibe coding), quindi i report sono in italiano semplice. Sotto il cofano: 9 skill, 5 agenti specializzati, hook PreToolUse/PostToolUse con script Bash e Python 3.

## Requisiti

- Claude Code (CLI) su macOS o Linux, versione recente (`claude --version`, testato su 2.1.198).
- Bash, Git, grep e Python 3.8 o successivo obbligatori. Scanner dello stack (es. npm audit, pip-audit) e database raggiungibile sono necessari per completare il relativo audit; la loro assenza deve lasciare il gate incompleto.

## Installazione (2 minuti)

1. Scompatta la cartella dove preferisci.
2. In una sessione Claude Code qualsiasi:
   ```
   /plugin marketplace add /percorso/della/cartella/scompattata
   /plugin install vibe-shield@vibe-shield-marketplace
   /reload-plugins
   ```
3. Verifica: `/vibe-shield:security-help` deve rispondere.

Per disinstallare: `/plugin uninstall vibe-shield` e `/plugin marketplace remove vibe-shield-marketplace`.

## Percorso di test suggerito

Su un progetto di prova (o una copia di uno vero):

1. `/vibe-shield:setup-security` — blindatura preventiva
2. Chiedi a Claude di scrivere in un file una chiave finta con formato reale (es. `sk_live_...` di 24+ caratteri): deve arrivare subito l'avviso dell'hook
3. Chiedi a Claude di committare quel file: il commit deve essere BLOCCATO (anche con `git add X && git commit` in un comando solo)
4. Chiedi di fare push: deve essere bloccato finché `/vibe-shield:pre-deploy` non passa
5. `/vibe-shield:security-audit` su un progetto con vulnerabilità note (SQL concatenato, CORS *, RLS assente...) e valuta qualità e falsi positivi del report
6. Se hai un tuo sito online: `/vibe-shield:post-deploy-check https://tuosito.tld`

## Quello che ci interessa davvero: prova a romperlo

Sei esperto di sicurezza: fai red teaming delle protezioni.

- Formati di segreti che sfuggono ai pattern (`scripts/patterns-exact.grep`)
- Modi di committare o pubblicare che aggirano gli hook (comandi composti, alias, script intermedi, tool diversi da Bash)
- Falsi positivi fastidiosi (c'è l'allowlist in `.vibe-shield/allowlist`, una ERE per riga)
- Prompt injection: un file malevolo nel progetto può convincere gli agenti a ignorare o falsificare un finding?
- Qualità dell'audit: finding gonfiati, mancati, gravità sbagliate; efficacia del verificatore avversariale
- Robustezza degli script (`scripts/`): parsing JSON, fail-open abusabile, edge case git

Nota dichiarata: gli hook proteggono solo ciò che passa da Claude Code; per il resto c'è il template CI (`templates/security-ci.yml`). Il bypass documentato `VIBE_SHIELD_SKIP=1` è una scelta consapevole di design.

## Feedback

Segnala per ogni problema: cosa hai fatto, cosa ti aspettavi, cosa è successo (con output). Anche due righe vanno benissimo. Grazie!

## Regressioni automatiche

Dalla radice del plugin:

```bash
python3 -m unittest discover -s tests
```

Le prove usano repository temporanei e credenziali sintetiche; non pubblicare segreti veri per testare il tool. Controllare almeno: segreto nello stage ma rimosso dal working tree, segreto già committato, commit e push concatenati, `git -C` su un altro repository, modifica successiva al pass, pass scaduto anche sullo stesso HEAD e fallimento che invalida un vecchio pass. Questi test dei guard non sostituiscono il collaudo reale nell’host.

## Flussi delle skill e costo

1. Un audit limitato a una cartella deve produrre un report parziale e gate incompleto.
2. Scanner mancante, errore di rete/database o verifica interrotta devono impedire il pass anche con zero finding.
3. Pre-deploy deve riusare solo un audit completo valido dello stesso contenuto. Un controllo extra fallito deve lasciare il gate bloccato.
4. Fix-security deve richiedere nuova verifica e copertura completa; azzerare i conteggi non basta a scrivere pass.
5. Confrontare audit vecchio e nuovo sullo stesso fixture, modello e configurazione dell’host, in sessioni separate: registrare token input/output/cache se disponibili, durata, numero di deleghe, copertura, finding confermati e vulnerabilità note mancate. Separare il caso di primo audit dal riuso in pre-deploy. Ripetere su più stack prima di concludere che il risparmio non peggiora la qualità.
6. Se l’host non espone token o tempi, segnare “non disponibile”. Non inferire un risparmio percentuale dal solo numero di agenti.

Gli agenti devono ereditare il modello della sessione e rispettare gli override espliciti. Un test nell’host deve confermare anche questo comportamento. La presenza delle skill in un host diverso da Claude Code non prova che esso esegua gli hook.

### Scanner e copertura

`scan-secrets.sh .` restituisce 0 senza match, 2 con risultati, 3 se incompleto o in errore. `scan-secrets.sh --history --all` controlla la storia disponibile, segnalando incompleta una clone shallow. I valori dei segreti non sono stampati. Blob identici della storia vengono scansionati una sola volta per contenuto; nomi e allowlist restano valutati separatamente.

Le prove del template CI verificano instradamento e soglia con comandi simulati. Non sostituiscono un’esecuzione su GitHub o l’accesso ai database degli scanner.
