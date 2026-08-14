# 🎬 Trakt Sync Tool

Script Python per sincronizzare watchlist, history e watched status su [Trakt.tv](https://trakt.tv/) partendo da dati IMDB.

## 📋 Indice

- [Funzionalità¶¶](#-funzionalità¶¶)
- [Requisiti](#-requisiti)
- [Installazione](#-installazione)
- [Configurazione](#-configurazione)
- [Utilizzo](#-utilizzo)
- [Struttura output](#-struttura-output)
- [Debug mode](#-debug-mode)
- [Note](#-note)

---

## ✨ Funzionalità¶¶

- 🔄 **Sincronizzazione bidirezionale**: gestisce watchlist, history e watched status
- 📺 **Supporto completo**: film e serie TV con stagioni/episodi
- 💾 **Caching intelligente**: riduce le chiamate API con cache SQLite persistente
- 🐛 **Debug mode**: salvataggio dati intermedi per troubleshooting
- ☁️ **Upload automatico**: invio diretto a Trakt (opzionale)
- 📊 **Logging dettagliato**: output chiaro con emoji e statistiche

---

## 📦 Requisiti

- Python 3.8+
- Account Trakt.tv con API credentials
- File di input già generati da Nuvio (`in/nuviosync-backup-Brrake.json`)

### Dipendenze

```bash
pip install requests requests-cache python-dotenv
```

Oppure:

```bash
pip install -r requirements.txt
```

---

## 🚀 Installazione

1. **Clona o scarica lo script**:
   ```bash
   git clone <repository-url>
   cd trakt-sync
   ```

2. **Installa le dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Crea il file `.env`**:
   ```bash
   cp .env.example .env
   ```

---

## ⚙️ Configurazione

Crea un file `.env` nella root del progetto con le seguenti variabili:

```env
# 🔑 Trakt API Credentials
TRAKT_CLIENT_ID=201dc70c5ec6af530f12f079ea1922733f6e1085ad7b02f36d8e011b75bcea7d
TRAKT_ACCESS_TOKEN=SXZOlBlGbwXxiSRVuqLYPbBDkBJwUpSA

# 🌐 Trakt API Endpoints
TRAKT_IMBD_SEARCH_URL=https://api.trakt.tv/search/imdb/
TRAKT_WATCHLIST_URL=https://api.trakt.tv/sync/watchlist
TRAKT_HISTORY_URL=https://api.trakt.tv/sync/history
TRAKT_WATCHED_URL=https://api.trakt.tv/users/me/lists/gia-visti/items

# ⚡ Configurazione
NUVIO_BACKUP_FILE=in/nuviosync-backup-Brrake.json
DEBUG=false
UPLOAD_ON_TRAKT=trueon

```

### Come ottenere le credenziali Trakt

1. Vai su [Trakt API Apps](https://trakt.tv/oauth/applications)
2. Crea una nuova applicazione
3. Copia **Client ID** e genera un **Access Token**
4. Inseriscili nel file `.env`

---

## 🎯 Utilizzo

### Esecuzione base

```bash
python sync.py
```

### Con upload su Trakt

Imposta `UPLOAD_ON_TRAKT=true` nel file `.env`:

```env
UPLOAD_ON_TRAKT=true
```

Poi esegui:

```bash
python sync.py
```

### Con debug mode

Per salvare dati intermedi nella cartella `debug/`:

```env
DEBUG=true
```

---

## 📁 Struttura output

### File generati

```
out/
├── sync/
│   ├── trakt_sync.json          # Watchlist finale (film + serie)
│   ├── trakt_history_sync.json  # History completa
│   └── trakt_watched_sync.json  # Watched status
└── res/                         # (solo se UPLOAD_ON_TRAKT=true)
    ├── watchlist.json           # Risposta API watchlist
    ├── history_del.json         # Risposta API delete history
    ├── history.json             # Risposta API insert history
    └── watched.json             # Risposta API watched
```

### File di debug

```
debug/
├── shows_data.json    # Dati serie TV prima dell'elaborazione
└── movies_data.json   # Dati film prima dell'elaborazione
```

---

## 🐛 Debug mode

Abilita la modalità debug per:

- Salvare i dati grezzi prima dell'elaborazione
- Avere logging più dettagliato
- Isolare problemi di formattazione dati

```env
DEBUG=true
```

I file di debug sono utili per:
- Verificare la struttura dei dati in input
- Controllare che tutti gli IMDB ID siano presenti
- Analizzare problemi di sincronizzazione

---

## 📊 Output logging

Lo script produce un output strutturato come:

```
============================================================
🎬  TRAKT SYNC - Sincronizzazione Watchlist & History
============================================================

📦 Generazione dati primari...
✅ Dati primari generati

📂 Caricamento dati da file...
✅ Caricati 150 elementi totali

🔄 Processamento elementi...
✅ Processati: 120 episodi, 25 film, 5 serie
⚠️  Saltati 3 elementi incompleti

────────────────────────────────────────────────────────────
📺  ELABORAZIONE SERIE TV
────────────────────────────────────────────────────────────

[1/5] 📺 Processing show tt0944947...
  🌐 API: tt0944947 (show)
  ✅ Il Trono di Spade - 8 stagione/i

────────────────────────────────────────────────────────────
💾  SALVATAGGIO FILE
────────────────────────────────────────────────────────────
  ✅ out/sync/trakt_sync.json
  ✅ out/sync/trakt_history_sync.json
  ✅ out/sync/trakt_watched_sync.json

============================================================
📊  RIEPILOGO FINALE
============================================================

✅ Operazione completata con successo!

📦 Dati elaborati:
   • Film in watchlist: 25
   • Serie TV in watchlist: 5
   • Film in history: 18
   • Serie TV in history: 4
   • Film in watched: 18
   • Serie TV in watched: 4

📺 Dettagli serie TV:
   • Totale stagioni: 42
   • Totale episodi: 387
```

---

## ⚠️ Note

### Rate limiting

Lo script include automaticamente un delay di **1 secondo** tra le chiamate API reali (non cached) per rispettare i limiti di Trakt.

### Cache

Le chiamate API sono cached indefinitamente in `cache/trakt_cache.sqlite`. Per forzare il refresh:

```bash
rm cache/trakt_cache.sqlite
```

### Formattazione date

Le date sono convertite nel formato ISO 8601 richiesto da Trakt:
```
YYYY-MM-DDTHH:MM:SS.000Z
```

### Errori comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| `401 Unauthorized` | Token scaduto o errato | Rigenera l'access token su Trakt |
| `404 Not Found` | IMDB ID non trovato | Verifica che l'ID sia corretto |
| `429 Too Many Requests` | Rate limiting | Attendi qualche minuto e riprova |
| `FileNotFoundError` | File di input mancanti | Esegui prima `generate_primary_json()` |

---

## 📝 License

Questo progetto è fornito così com'è per uso personale.

---

## 🤝 Supporto

Per problemi o domande:

1. Abilita la debug mode (`DEBUG=true`)
2. Controlla i file in `debug/`
3. Verifica le risposte API in `out/res/` (se `UPLOAD_ON_TRAKT=true`)

---

**Happy syncing!** 🎬📺✨