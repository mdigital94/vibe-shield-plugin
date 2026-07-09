# Checklist mirate per stack

Consultate da security-audit: individua lo stack del progetto e passa la sezione pertinente agli agenti come contesto aggiuntivo. Non applicare checklist di stack assenti.

## Next.js / React / SPA

- Segreti in variabili NEXT_PUBLIC_ / VITE_ / REACT_APP_ (finiscono nel bundle, leggibili da chiunque)
- API route senza controllo di sessione (getServerSession/middleware assenti su route che toccano dati)
- Middleware di auth che esclude percorsi per errore (matcher troppo stretti)
- dangerouslySetInnerHTML con dati non sanificati
- Sourcemap in produzione (productionBrowserSourceMaps)
- Server Actions senza validazione dell'input e senza controllo di autorizzazione
- Redirect basati su parametri (open redirect)

## Supabase

- Tabelle senza `enable row level security` nelle migration
- Policy `using (true)` o `with check (true)` in scrittura
- service_role in file esposti al client o in variabili con prefisso pubblico
- Storage bucket pubblici con contenuti privati
- Funzioni RPC (postgres functions) `security definer` che aggirano le RLS senza controlli interni
- Auth: conferma email disattivata su app con dati sensibili

## Firebase

- firestore.rules / database.rules.json / storage.rules con `allow read, write: if true` o regole scadute (date di test)
- Regole che controllano solo `request.auth != null` su dati che dovrebbero essere per-utente (chiunque loggato legge tutto)
- serviceAccountKey/adminsdk json nel repo
- Cloud Functions senza controllo di auth sull'invocatore

## Express / Node backend

- app.use(cors()) senza opzioni (equivale a origin *)
- Query SQL con template string, exec/spawn con input utente
- express-session: cookie senza httpOnly/secure/sameSite, secret hardcodato
- Nessun rate limit su /login, /register, /reset
- body-parser senza limite di dimensione
- Upload multer senza filtro tipo/dimensione, salvati in cartella statica
- helmet assente

## Python (FastAPI / Flask / Django)

- DEBUG=True, SECRET_KEY hardcodata, ALLOWED_HOSTS=['*'] (Django)
- f-string/format nelle query (anche con ORM: raw/extra)
- CORSMiddleware con allow_origins=['*'] insieme a allow_credentials=True
- pickle/yaml.load su input esterno (deserializzazione)
- subprocess con shell=True e input utente

## Docker / docker-compose

- USER root (nessun USER dichiarato), segreti in ENV/ARG nel Dockerfile
- docker-compose committato con password reali nei service environment
- Porte DB pubblicate su 0.0.0.0 senza necessità
- Immagini base non aggiornate (FROM molto vecchi)

## GitHub Actions

- Segreti scritti in chiaro nei workflow invece di ${{ secrets.X }}
- pull_request_target con checkout del ref del PR
- Action di terzi con @main/@master invece di tag o SHA, in workflow con accesso a segreti
- `run` che stampa segreti nei log

## Siti statici (Netlify/Vercel/GitHub Pages)

- File di troppo nella cartella pubblicata: .env, .git, backup, note
- Form che postano verso endpoint senza protezione anti spam
- Chiavi API "nascoste" nel JS (sul frontend nulla è nascosto: se una chiave deve restare segreta, serve un backend o una function)
