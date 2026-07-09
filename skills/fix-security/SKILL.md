---
name: fix-security
description: Corregge in modo guidato i problemi trovati dall'audit di sicurezza: applica automaticamente i fix sicuri e spiega in linguaggio semplice quelli che richiedono una decisione. Usalo dopo security-audit o pre-deploy, o quando l'utente chiede di sistemare i problemi di sicurezza.
argument-hint: "[gravità minima da correggere, opzionale: critici|alti|tutti]"
---

# Fix Security

Correggi i problemi di sicurezza del progetto partendo dal report dell'ultimo audit. L'utente non ha competenze tecniche: applica tu ciò che è sicuro applicare e spiega in italiano semplice ciò che richiede una sua decisione.

## Procedura

### 1. Recupera i finding

- Leggi `.vibe-shield/report.md`. Se non esiste o il codice è cambiato molto dall'audit, esegui prima la skill `security-audit`.
- Filtra secondo $ARGUMENTS se specificato (default: tutti, in ordine di gravità).

### 2. Applica i fix, uno alla volta

Procedi dal CRITICO al BASSO. Per ogni finding:

**Se AUTO_FIX = SI**, applica direttamente. Esempi di fix considerati sicuri:
- Spostare segreti in .env, aggiornare .gitignore e .env.example, sostituire con variabili d'ambiente.
- Parametrizzare query SQL costruite con concatenazione (stesso comportamento, input trattato come dato).
- Aggiungere security header nella config della piattaforma.
- Aggiungere i flag HttpOnly, Secure, SameSite ai cookie di sessione.
- Sostituire innerHTML con textContent quando il contenuto è testo semplice.
- Sostituire Math.random con il generatore crittografico dello stack per token e codici.
- Aggiornare dipendenze vulnerabili a versioni patch o minor.
- Spegnere debug/verbose error in produzione.

**Se AUTO_FIX = NO**, non applicare: spiega all'utente in 2-3 frasi semplici il problema, cosa comporta la correzione e le opzioni, poi chiedi cosa preferisce. Esempi tipici: abilitare RLS su Supabase (bisogna decidere chi può vedere cosa), aggiungere autenticazione a un endpoint aperto, aggiornamenti major di dipendenze, riscrivere la storia git, rigenerare chiavi.

Regola del minimo intervento: ogni fix tocca solo ciò che serve, nello stile del codice esistente. Niente refactoring di contorno.

### 3. Verifica ogni fix

Dopo ogni gruppo di fix:
- Se il progetto ha un comando di build o test, eseguilo e verifica che passi.
- Se non ha test, verifica almeno che l'app si avvii o che la sintassi sia valida.
- Se un fix rompe qualcosa, fai rollback di quel fix e riclassificalo come "richiede decisione umana", spiegando perché.

### 4. Chiudi il giro

1. Aggiorna `.vibe-shield/report.md` marcando ogni finding come RISOLTO, RESPINTO (fix fallito, spiegare) o IN ATTESA DI DECISIONE.
2. Se restano zero critici, zero alti e zero medi, riesegui il gate:
   ```
   bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" pass <critici> <alti> <medi> <bassi>
   ```
   Altrimenti scrivi `fail` con i conteggi aggiornati.
3. Riassumi in italiano semplice: cosa hai corretto (con il perché in una frase ciascuno), cosa resta da decidere e qual è il prossimo passo. Se resta qualcosa di critico, alto o medio, di' chiaramente che il progetto non va ancora pubblicato.

## Regole

- Mai applicare in autonomia fix che cambiano il comportamento visibile dell'app o che richiedono scelte di prodotto.
- Mai `npm audit fix --force`.
- Mai riscrivere la storia git senza conferma esplicita.
- Se l'utente ha fretta e chiede di "sistemare tutto e basta", applica comunque solo i fix sicuri e sii onesto sul resto.
