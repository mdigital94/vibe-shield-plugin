---
name: incident-response
description: Guida di emergenza quando il danno è già avvenuto o si sospetta: chiave esposta e già pubblicata, sito compromesso, dati trafugati, attività strane, addebiti anomali. Usalo quando l'utente dice cose come "sono stato hackerato", "ho pubblicato una chiave", "c'è attività strana", "mi sono arrivati addebiti assurdi".
---

# Incident Response

L'utente sospetta o ha subito un incidente di sicurezza. Probabilmente è nel panico: mantieni un tono calmo e concreto, un passo alla volta, in italiano semplicissimo. Prima si ferma l'emorragia, poi si capisce cosa è successo, poi si sistema la causa.

## 0. Triage: capisci la situazione (2 domande, non di più)

1. Cosa è successo o cosa hai notato? (chiave pubblicata, addebiti strani, dati modificati, email dagli utenti, avviso da GitHub/provider...)
2. Il progetto è online e ha utenti reali con dati veri?

In base alle risposte, procedi nell'ordine sotto. Non fare l'audit completo adesso: prima si tampona.

## 1. Ferma l'emorragia (i primi 15 minuti)

**Chiave o password esposta (il caso più comune):**
1. REVOCA SUBITO la chiave dal pannello del servizio che l'ha emessa. Guida l'utente al posto giusto in base al tipo di chiave: Stripe (dashboard.stripe.com, sezione Developers, API keys), OpenAI (platform.openai.com, API keys), Anthropic (console.anthropic.com), Google/Gemini (console.cloud.google.com, Credenziali), AWS (console IAM), Supabase (dashboard, Settings, API), GitHub (Settings, Developer settings, Tokens), database (cambia la password dell'utente DB).
2. Genera la chiave nuova e mettila SOLO nel .env locale e nelle variabili d'ambiente della piattaforma di deploy. Mai nel codice.
3. Rimuovere la chiave dal codice NON basta: se è stata pubblicata (GitHub, sito online), è compromessa per sempre. La revoca è l'unica cura. I bot trovano le chiavi esposte su GitHub in pochi MINUTI.

**Sospetta compromissione del sito o dei dati:**
1. Se il danno è attivo e grave (dati che spariscono, spam inviato dal sito, costi che salgono): metti il sito offline o in manutenzione dal pannello della piattaforma. Meglio un sito fermo che un sito che danneggia.
2. Cambia le password degli account di piattaforma (GitHub, Vercel/Netlify, database, email collegata) e attiva la 2FA se non c'è.
3. Revoca le sessioni attive dove possibile (GitHub: Settings, Sessions; Supabase: rigenera i JWT secret, che invalida i token in circolazione).

**Addebiti anomali su un servizio a consumo:**
1. Revoca subito le chiavi di quel servizio (vedi sopra).
2. Imposta un limite di spesa o disattiva la fatturazione dal pannello.
3. Contatta il supporto del servizio: spiegando l'abuso, spesso stornano i costi.

## 2. Valuta il danno

1. Da quanto tempo era esposta la falla? (data del commit incriminato: `git log` sul file; data del deploy)
2. Cosa poteva fare chi la sfruttava? (leggere dati? scrivere? spendere soldi? impersonare utenti?)
3. Controlla i segnali: log di accesso della piattaforma e del database, dashboard di utilizzo delle API (consumi anomali), integrità dei dati (record modificati o spariti), file sospetti nel progetto.
4. Se il database conteneva dati personali di utenti reali e c'è evidenza concreta di accesso non autorizzato: spiega all'utente, senza allarmismo ma onestamente, che in UE il GDPR può richiedere la notifica al Garante entro 72 ore e l'avviso agli utenti coinvolti, e che per questo caso specifico è il momento di sentire una persona esperta (o un legale), non solo un tool.

## 3. Chiudi la falla

1. Esegui la skill `secrets-scan` (bonifica di codice e storia git) e poi `security-audit` completo: chi è entrato da una porta potrebbe aver trovato le altre aperte.
2. Applica i fix con `fix-security`.
3. Se la chiave era nella storia git di un repo pubblico: oltre alla revoca (già fatta), pulisci la storia o, spesso più semplice, valuta di ricreare il repository pulito.
4. Ripubblica solo dopo che `pre-deploy` passa.

## 4. Dopo l'incendio

Riassumi all'utente in italiano semplice: cosa è successo, cosa avete fatto, cosa resta da monitorare nei prossimi giorni (consumi, log, email degli utenti). Poi le tre abitudini che evitano il bis: 2FA su tutti gli account, chiavi solo in .env e nei pannelli (mai nel codice), e `pre-deploy` prima di ogni pubblicazione, sempre.

## Regole

- Ordine rigido: prima revocare/contenere, poi indagare, poi sistemare. Mai invertire.
- Non promettere che "è tutto risolto": di' cosa è stato fatto e cosa resta incerto.
- Non riportare mai valori di segreti nei messaggi o nei report.
