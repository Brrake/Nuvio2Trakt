# 🎬 Trakt Sync Tool

Utility Python per convertire un backup Nuvio in file compatibili con Trakt e, opzionalmente, caricarli tramite API.

## Funzionalità

- 📥 Legge un backup Nuvio da `NUVIO_BACKUP_FILE`.
- 🎬 Gestisce film e serie TV.
- 📺 Mantiene gli episodi visti con stagione, episodio e timestamp.
- 🕘 Genera file intermedi per watchlist e history.
- 🌐 Risolve gli IMDB ID tramite Trakt Search API.
- 💾 Usa una cache SQLite persistente per evitare richieste ripetute.
- ☁️ Può aggiornare watchlist, history e watched status su Trakt.
- 🐛 Offre file intermedi di debug e logging con emoji.

> Nota: `UPLOAD_ON_TRAKT=true` esegue operazioni distruttive sulla history: prima la rimuove e poi la reinserisce. Usa questa modalità solo dopo avere verificato i JSON generati localmente.

## Requisiti

- Python 3.10 o superiore.
- Un backup Nuvio valido.
- Un'applicazione Trakt e un access token valido.

Installa le dipendenze:

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` dovrebbe contenere almeno:

```text
python-dotenv
requests
requests-cache
```

## Installazione

```bash
git clone <repository-url>
cd trakt-sync
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows PowerShell
python -m pip install -r requirements.txt
cp .env.example .env
```

Inserisci il backup nella posizione indicata da `NUVIO_BACKUP_FILE`, oppure specifica un percorso assoluto nel file `.env`.

## Configurazione

Esempio `.env`:

```env
TRAKT_CLIENT_ID=your_client_id
TRAKT_ACCESS_TOKEN=your_access_token

TRAKT_IMBD_SEARCH_URL=https://api.trakt.tv/search/imdb/
TRAKT_WATCHLIST_URL=https://api.trakt.tv/sync/watchlist
TRAKT_HISTORY_URL=https://api.trakt.tv/sync/history
TRAKT_WATCHED_URL=https://api.trakt.tv/users/me/lists/gia-visti/items

NUVIO_BACKUP_FILE=in/nuviosync-backup-Brrake.json
DEBUG=false
UPLOAD_ON_TRAKT=false
```

Non committare mai `.env`: contiene credenziali sensibili. Usa `.env.example` solo con valori segnaposto.

### Credenziali Trakt

1. Apri [Trakt API Applications](https://trakt.tv/oauth/applications).
2. Crea un'applicazione.
3. Copia il Client ID.
4. Genera un access token OAuth.
5. Inserisci i valori nel file `.env`.

## Utilizzo

### 1. Generazione dei file intermedi

La funzione viene eseguita automaticamente da `sync.py`, ma può essere testata separatamente:

```bash
python utils/generate.py
```

Questo produce:

```text
out/trakt_watchlist.json
out/trakt_history.json
```

### 2. Sincronizzazione locale

Esegui lo script senza upload per controllare l'output:

```bash
UPLOAD_ON_TRAKT=false python sync.py
```

Su Windows imposta `UPLOAD_ON_TRAKT=false` nel `.env`.

### 3. Upload su Trakt

Dopo avere verificato i file locali:

```env
UPLOAD_ON_TRAKT=true
```

Poi esegui:

```bash
python sync.py
```

L'upload esegue, nell'ordine:

1. Aggiornamento della watchlist.
2. Rimozione della history inviata.
3. Reinserimento della history.
4. Aggiornamento del watched status.

## Formato input Nuvio

Il backup deve contenere una struttura simile a:

```json
{
  "original": {
    "library": [
      {
        "content_id": "tt1234567",
        "content_type": "movie",
        "added_at": 1700000000000
      }
    ],
    "watched": [
      {
        "content_id": "tt1234567",
        "watched_at": 1700000000000,
        "season": 1,
        "episode": 1
      }
    ]
  }
}
```

I timestamp Nuvio sono interpretati come Unix timestamp in millisecondi e convertiti in UTC ISO-8601.

## Output

```text
out/
├── trakt_watchlist.json
├── trakt_history.json
├── sync/
│   ├── trakt_sync.json
│   ├── trakt_history_sync.json
│   └── trakt_watched_sync.json
└── res/
    ├── watchlist.json
    ├── history_del.json
    ├── history.json
    └── watched.json
```

La directory `out/res` viene creata solo quando l'upload è abilitato.

## Cache

Le risposte della Search API vengono salvate nella cache SQLite sotto `cache/`.

Per forzare una nuova risoluzione degli ID:

```bash
rm -rf cache/
```

Su Windows elimina manualmente la directory `cache`.

La cache è persistente e non ha scadenza; valuta di cancellarla se Trakt restituisce dati aggiornati o se cambi endpoint.

## Debug e troubleshooting

Con:

```env
DEBUG=true
```

vengono salvati dati intermedi in:

```text
debug/shows_data.json
debug/movies_data.json
```

Errori comuni:

| Errore | Possibile causa | Azione |
|---|---|---|
| `FileNotFoundError` | Backup o file intermedi assenti | Controlla `NUVIO_BACKUP_FILE` e la directory di esecuzione |
| `401 Unauthorized` | Token scaduto o credenziali errate | Rigenera l'access token |
| `404 Not Found` | Endpoint o IMDB ID errato | Verifica URL e dati input |
| `429 Too Many Requests` | Limite API superato | Attendi e lascia attiva la cache |
| `JSONDecodeError` | Backup o risposta API non validi | Valida il JSON e conserva la risposta in `out/res` |

## Sicurezza

- Mantieni `.env`, backup Nuvio, `cache/`, `out/` e `debug/` fuori dal repository.
- Revoca immediatamente eventuali token Trakt esposti.
- Non inserire credenziali reali nel README o in `.env.example`.
- Testa sempre con `UPLOAD_ON_TRAKT=false` prima di modificare dati remoti.

## Struttura consigliata

```text
.
├── sync.py
├── utils/
│   └── generate.py
├── requirements.txt
├── .env.example
├── .gitignore
├── in/
├── out/
├── cache/
└── debug/
```

## Limitazioni note

- La risoluzione dei contenuti dipende dall'IMDB ID presente nel backup.
- La cronologia viene ricostruita in base ai dati `watched` disponibili nel backup.
- Lo script non dovrebbe essere eseguito contemporaneamente in più processi sullo stesso file di cache.
- Prima dell'upload è consigliabile creare una copia dei JSON generati.

## Licenza

Uso personale. Aggiungi qui la licenza del progetto se prevedi di pubblicarlo.