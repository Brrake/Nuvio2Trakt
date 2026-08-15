import os
import requests
import json
import dotenv
import requests_cache
import time
from pathlib import Path
dotenv.load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# 🔧 Configurazione
# ─────────────────────────────────────────────────────────────────────────────
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID", "")
TRAKT_ACCESS_TOKEN = os.getenv("TRAKT_ACCESS_TOKEN", "")
TRAKT_IMBD_SEARCH_URL = os.getenv("TRAKT_IMBD_SEARCH_URL", "")
TRAKT_WATCHLIST_URL = os.getenv("TRAKT_WATCHLIST_URL", "")
TRAKT_HISTORY_URL = os.getenv("TRAKT_HISTORY_URL", "")
TRAKT_WATCHED_URL = os.getenv("TRAKT_WATCHED_URL", "")

script_dir = Path(__file__).resolve().parent
project_dir = script_dir.parent
RES_PATH = Path(project_dir / "out/res")
RES_PATH.mkdir(exist_ok=True)

CACHE_DIR = Path(project_dir / "cache")
CACHE_DIR.mkdir(exist_ok=True)

trakt_session = requests_cache.CachedSession(
    str(CACHE_DIR / "trakt_cache"),
    backend="sqlite",
    expire_after=None
)
headers = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
    "Authorization": f"Bearer {TRAKT_ACCESS_TOKEN}",
}

# ─────────────────────────────────────────────────────────────────────────────
# 🌐 Funzione API Trakt
# ─────────────────────────────────────────────────────────────────────────────
def get_trakt_info(imdb_id, media_type):
    """Recupera informazioni da Trakt API per un IMDB ID."""
    url = f"{TRAKT_IMBD_SEARCH_URL}{imdb_id}?type={media_type}"
    
    try:
        response = trakt_session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            if response.from_cache:
                print(f"  💾 Cache: {imdb_id} ({media_type})")
            else:
                print(f"  🌐 API: {imdb_id} ({media_type})")
                time.sleep(1)  # Rate limiting solo per richieste reali
            return response.json()
        else:
            print(f"  ❌ Errore API {response.status_code} per {imdb_id}")
            
    except requests_cache.requests.exceptions.RequestException as e:
        print(f"  ❌ Errore richiesta: {e}")
    except ValueError as e:
        print(f"  ❌ JSON non valido: {e}")
    
    return None

def delete_from_trakt_history(trakt_json):
    """Rimuove i dati dalla cronologia di Trakt in base ai dati forniti"""
    print("\n🗑️  Pulizia history...")
    response_del_history = requests.post(url=TRAKT_HISTORY_URL+'/remove', headers=headers, json=trakt_json)
    
    if response_del_history.status_code in [200, 201]:
        print("  ✅ History ripulita")
        with open(f'{RES_PATH}/history_del.json', 'w', encoding='utf-8') as f:
            json.dump(response_del_history.json(), f, indent=2, ensure_ascii=False)
    else:
        print(f"  ⚠️  Errore pulizia history: {response_del_history.status_code}")

def add_to_trakt_history(trakt_json):
    """Invia i dati alla cronologia di Trakt"""
    print("\n📤 Invio history...")
    response_history = requests.post(url=TRAKT_HISTORY_URL, headers=headers, json=trakt_json)

    if response_history.status_code in [200, 201]:
        with open(f'{RES_PATH}/history.json', 'w', encoding='utf-8') as f:
            json.dump(response_history.json(), f, indent=2, ensure_ascii=False)
        print("  ✅ History importata su Trakt!")
    else:
        print(f"  ⚠️  Errore history: {response_history.status_code}")

def add_to_trakt_watchlist(trakt_json):
    """Invia i dati alla watchlist di Trakt"""
    print("\n📤 Invio watchlist...")
    response_watchlist = requests.post(url=TRAKT_WATCHLIST_URL, headers=headers, json=trakt_json)
    
    if response_watchlist.status_code in [200, 201]:
        with open(f'{RES_PATH}/watchlist.json', 'w', encoding='utf-8') as f:
            json.dump(response_watchlist.json(), f, indent=2, ensure_ascii=False)
        print("  ✅ Watchlist importata su Trakt!")
    else:
        print(f"  ⚠️  Errore watchlist: {response_watchlist.status_code}")