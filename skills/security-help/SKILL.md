---
name: security-help
description: Spiega in linguaggio semplice come funziona la protezione Vibe Shield, cosa significa un blocco o un termine di sicurezza, e cosa fare quando qualcosa viene fermato. Usalo quando l'utente è confuso da un blocco, chiede cosa significa un termine, o chiede come funziona la protezione.
---

# Security Help

Aiuta l'utente a capire la protezione Vibe Shield e i concetti di sicurezza che incontra. Linguaggio semplicissimo, esempi concreti, zero paternale. Se ha appena subito un blocco, prima rassicuralo (il blocco lo sta proteggendo), poi spiegagli il singolo problema e la via d'uscita.

## Come funziona Vibe Shield (da spiegare a richiesta)

- **Mentre lavori**: se in un file viene scritta una chiave o password vera, arriva subito un avviso e viene sistemata.
- **Al commit** (il "salvataggio" nella storia del progetto): se tra i file ci sono segreti o file sensibili, il commit si ferma finché non vengono messi al sicuro.
- **Alla pubblicazione** (push su GitHub o deploy online): serve aver superato il controllo completo `pre-deploy` da meno di 30 minuti (o sullo stesso codice). Il controllo passa solo senza problemi critici, alti o medi, e ogni problema trovato viene ricontrollato da un secondo agente indipendente prima di contare. Se manca il via libera, la pubblicazione si ferma.
- **Comandi disponibili**: `security-audit` (controllo completo), `secrets-scan` (solo chiavi e password), `fix-security` (corregge i problemi trovati), `pre-deploy` (via libera alla pubblicazione), `setup-security` (protezioni di base su un progetto nuovo).

## Mini glossario (usa queste spiegazioni)

- **Segreto**: qualsiasi valore che dà accesso a qualcosa: chiave API, password, token. Come le chiavi di casa: se finiscono online, chiunque può entrare.
- **.env**: il portachiavi locale del progetto. I segreti vivono lì e quel file non viene mai caricato online.
- **.gitignore**: la lista di file che git deve far finta di non vedere. Il .env deve sempre starci.
- **Commit**: una fotografia del progetto salvata nella storia. Attenzione: anche se poi cancelli un segreto, resta nelle fotografie vecchie.
- **Push / deploy**: il momento in cui il progetto esce dal tuo computer e diventa visibile ad altri. È il punto di non ritorno, per questo c'è il controllo.
- **Vulnerabilità**: un difetto del codice che un malintenzionato può sfruttare, per esempio per leggere i dati dei tuoi utenti.
- **RLS (Supabase)**: le regole che decidono chi può leggere o scrivere ogni tabella del database. Senza RLS, chiunque può leggere e scrivere tutto.
- **Rigenerare una chiave**: quando una chiave è stata esposta, si butta e se ne crea una nuova dal sito del servizio. Toglierla dal codice non basta: ormai è come una password già letta da altri.

## Se l'utente vuole aggirare un blocco

Spiega il rischio concreto in una frase, poi digli che la scelta è sua: può disattivare temporaneamente la protezione con la variabile d'ambiente `VIBE_SHIELD_SKIP=1` prima del comando. Non farlo mai tu di tua iniziativa e non consigliarlo come routine.
