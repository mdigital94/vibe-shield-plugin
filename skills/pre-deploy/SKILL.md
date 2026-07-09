---
name: pre-deploy
description: Gate finale prima di pubblicare online o caricare su GitHub: audit completo, controlli specifici da deploy e apertura del blocco su push e deploy. Usalo quando l'utente vuole pubblicare, deployare, mettere online o caricare il progetto, o quando l'hook di Vibe Shield ha bloccato un push.
---

# Pre-Deploy

Sei il controllo finale prima che il progetto vada online. Il push o il deploy restano bloccati dall'hook di Vibe Shield finché questo gate non risulta superato. L'utente non ha competenze tecniche: guida tu tutto il processo.

## Procedura

### 1. Audit completo

- Se esiste un audit fresco e superato (`.vibe-shield/status.json` con result `pass`, stesso commit o più recente di 30 minuti) puoi riusarlo.
- Altrimenti esegui la skill `security-audit` per intero (4 agenti in parallelo, report, gate).

### 2. Controlli extra da deploy

Oltre all'audit, verifica questi punti specifici della pubblicazione:

1. **.gitignore efficace**: `.env` e i file sensibili risultano davvero ignorati (`git status` non li mostra, `git ls-files` non li contiene).
2. **Cosa finisce online**: controlla che nella cartella pubblicata non ci siano file di troppo (dump, backup, note con credenziali, cartelle di test). Per siti statici: il publish dir non contiene .env o .git.
3. **Variabili d'ambiente in produzione**: elenca all'utente le variabili che dovrà configurare sul pannello della piattaforma (Vercel, Netlify, ecc.), perché il .env locale non viene caricato. Spiega dove si fa, in breve.
4. **Build**: se il progetto ha un comando di build, eseguilo e verifica che vada a buon fine.
5. **Repo pubblico o privato**: se l'utente sta creando un repo GitHub, chiedi se dev'essere pubblico o privato e spiega la differenza in una frase.

### 3. Esito

**Se tutto è a posto (zero critici, zero alti, zero medi dopo la verifica incrociata):**
1. Assicurati che il gate sia scritto:
   ```
   bash "${CLAUDE_SKILL_DIR}/../../scripts/write-status.sh" pass <critici> <alti> <medi> <bassi>
   ```
2. Comunica in italiano semplice: "🟢 Controllo superato, puoi pubblicare. Il via libera vale 30 minuti o finché non modifichi il codice; dopo, rilancia questo controllo." Poi ricorda le variabili d'ambiente da impostare sulla piattaforma, se ce ne sono.

**Se ci sono problemi critici, alti o medi:**
1. NON scrivere il gate come pass.
2. Spiega i problemi in italiano semplice, uno per uno: cosa rischia in pratica se pubblica così.
3. Proponi di eseguire subito la skill `fix-security` e, a fix completati, rilancia questo gate.

## Regole

- Il gate `pass` si scrive SOLO con zero critici, zero alti e zero medi reali (confermati o incerti dopo la verifica incrociata). Mai scriverlo per far passare un push "perché l'utente ha fretta": il blocco esiste per proteggerlo. Se l'utente insiste per pubblicare comunque, spiega il rischio concreto e digli che esiste la variabile VIBE_SHIELD_SKIP=1 come scelta sua e consapevole; non usarla tu di iniziativa.
- Non mostrare mai valori di segreti.
