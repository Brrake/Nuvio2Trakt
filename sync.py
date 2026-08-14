import json
from datetime import datetime
from collections import defaultdict
from utils.generate import generate_primary_json
import requests
import time
import os
import dotenv
import requests_cache
from copy import deepcopy
dotenv.load_dotenv()
from pathlib import Path
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID", "")
TRAKT_ACCESS_TOKEN = os.getenv("TRAKT_ACCESS_TOKEN", "")
TRAKT_IMBD_SEARCH_URL = os.getenv("TRAKT_IMBD_SEARCH_URL", "")
UPLOAD_ON_TRAKT=os.getenv("UPLOAD_ON_TRAKT", "false") == "true"
TRAKT_WATCHLIST_URL= os.getenv("TRAKT_WATCHLIST_URL", "")
TRAKT_HISTORY_URL= os.getenv("TRAKT_HISTORY_URL", "")
TRAKT_WATCHED_URL= os.getenv("TRAKT_WATCHED_URL", "")
DEBUG=os.getenv("DEBUG", "false") == "true"
OUTPUT_FILE="out/sync/trakt_sync.json"
OUTPUT_HISTORY_FILE="out/sync/trakt_history_sync.json"
OUTPUT_WATCHED_FILE="out/sync/trakt_watched_sync.json"


CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
# Extract directory path from the file path
output_dir = os.path.dirname(OUTPUT_FILE)

# Create directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

trakt_session = requests_cache.CachedSession(
    str(CACHE_DIR / "trakt_cache"),
    backend="sqlite",
    expire_after=None
)

generate_primary_json()
# Leggi il tuo output.json
with open('out/trakt_watchlist.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
with open('out/trakt_history.json', 'r', encoding='utf-8') as f2:
    data += json.load(f2)

# Struttura per raggruppare gli episodi per serie
shows_data = defaultdict(lambda: {
    'imdb_id': None,
    'seasons': defaultdict(lambda: defaultdict(list)),
    'watchlisted_at': None,
    'watched_at': None
})

# Struttura per i film
movies_data = defaultdict(lambda: {
    'imdb_id': None,
    'watchlisted_at': None,
    'watched_at': None
})

def get_trakt_info(imdb_id, media_type):
    url = f"{TRAKT_IMBD_SEARCH_URL}{imdb_id}?type={media_type}"

    try:
        response = trakt_session.get(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            # True se la risposta è stata recuperata dalla cache
            if response.from_cache:
                print(f"✓ Cache: {imdb_id} ({media_type})")
            else:
                print(f"✓ API: {imdb_id} ({media_type})")

                # Rate limiting solo per richieste reali
                time.sleep(1)

            return response.json()

        print(f"✗ Errore API: {response.status_code}")

    except requests_cache.requests.exceptions.RequestException as e:
        print(f"✗ Errore richiesta API: {e}")
    except ValueError as e:
        print(f"✗ Risposta JSON non valida: {e}")

    return None
# Processa episodi e film
for item in data:
    imdb_id = item['imdb_id']
    if not imdb_id:
        continue
    watchlisted_at = item.get('watchlisted_at',None)
    watched_at = item.get('watched_at',None)

    if item['type'] == 'episode':
        season = item['season']
        episode = item['episode']

        # Salta dati incompleti
        if season is None or episode is None:
            continue

        #shows_data[imdb_id]['imdb_id'] = imdb_id
        shows_data[imdb_id]['seasons'][season][episode] = item.get('watched_at','')

    elif item['type'] == 'movie':
        # Se lo stesso film appare più volte, tieni l'ultimo watchlisted_at
        movies_data[imdb_id]['imdb_id'] = imdb_id
        if watchlisted_at is not None:
            movies_data[imdb_id]['watchlisted_at'] = watchlisted_at
        if watched_at is not None:
            movies_data[imdb_id]['watched_at'] = watched_at

    else:
        shows_data[imdb_id]['imdb_id'] = imdb_id
        shows_data[imdb_id]['watchlisted_at'] = watchlisted_at

# Header per le API Trakt
headers = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
    "Authorization": f"Bearer {TRAKT_ACCESS_TOKEN}",
}

final_shows = []
final_movies = []

final_watched_shows = []
final_watched_movies = []

final_history_shows = []
final_history_movies = []

if DEBUG:
    DEBUG_DIR = Path("debug")
    DEBUG_DIR.mkdir(exist_ok=True)
    with open('debug/shows_data.json', 'w', encoding='utf-8') as f:
        json.dump(shows_data, f, indent=2, ensure_ascii=False)
    with open('debug/movies_data.json', 'w', encoding='utf-8') as f:
        json.dump(movies_data, f, indent=2, ensure_ascii=False)

print("Recupero informazioni dalle serie TV...")


# Processa le serie TV
for imdb_id, show_info in shows_data.items():
    print(f"Processing show {imdb_id}...")
    results = get_trakt_info(imdb_id,'show')

    if results and len(results) > 0:
        show = results[0].get('show', {})
        show_ids = show.get('ids', {})
        try:
            dt = datetime.fromisoformat(show_info['watchlisted_at'].replace('+00:00', 'Z'))
            formatted_date = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except Exception:
            formatted_date = show_info['watchlisted_at']
        trakt_show = {
            'title': show.get('title', 'Unknown'),
            'year': show.get('year', 0),
            'ids': {
                'tvdb': show_ids.get('tvdb'),
                'imdb': imdb_id,
                'tmdb': show_ids.get('tmdb'),
                'trakt': show_ids.get('trakt')
            },
            'seasons': []
        }

        # Rimuovi i campi None dagli IDs
        trakt_show['ids'] = {k: v for k, v in trakt_show['ids'].items() if v is not None}

        # Costruisci le stagioni ed episodi
        for season_num, episodes in sorted(
            ((s, eps) for s, eps in show_info['seasons'].items() if s is not None),
            key=lambda x: x[0]
        ):
            season_obj = {
                'number': season_num,
                'episodes': []
            }

            # Filtra eventuali episode None e ordina per numero
            valid_episodes = [
                (ep, watched_at)
                for ep, watched_at in episodes.items()
                if ep is not None
            ]

            for ep_num, watched_at in sorted(valid_episodes, key=lambda x: x[0]):
                try:
                    dt = datetime.fromisoformat(watched_at.replace('+00:00', 'Z'))
                    formatted_date = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                except Exception:
                    formatted_date = watched_at

                season_obj['episodes'].append({
                    'number': ep_num,
                    'watched_at': formatted_date
                })

            trakt_show['seasons'].append(season_obj)
        if trakt_show['seasons'] == []:
            out = deepcopy(trakt_show)
            out.pop("seasons", None)
            if formatted_date is not None:
                out['watchlisted_at'] = formatted_date
            final_shows.append(out)
        else:
            final_history_shows.append(trakt_show)
            out = deepcopy(trakt_show)
            out.pop("seasons", None)
            out['watched_at'] = trakt_show['seasons'][-1]['episodes'][-1]['watched_at']
            final_watched_shows.append(out)
        print(f"  ✓ {show.get('title')} - {len(show_info['seasons'])} stagioni")
    else:
        print(f"  ✗ Serie non trovata: {imdb_id}")


print("\nRecupero informazioni dai film...")

# Processa i film
for imdb_id, movie_info in movies_data.items():
    print(f"Processing movie {imdb_id}...")

    results = get_trakt_info(imdb_id,'show')
    
    if results and len(results) > 0:
        movie = results[0].get('movie', {})
        movie_ids = movie.get('ids', {})

        # Formatta la data
        try:
            dt = datetime.fromisoformat(movie_info['watchlisted_at'].replace('+00:00', 'Z'))
            formatted_date = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except Exception:
            formatted_date = movie_info['watchlisted_at']

        trakt_movie = {
            'title': movie.get('title', 'Unknown'),
            'year': movie.get('year', 0),
            'ids': {
                'tvdb': movie_ids.get('tvdb'),
                'imdb': imdb_id,
                'tmdb': movie_ids.get('tmdb'),
                'trakt': movie_ids.get('trakt')
            }
        }
        # Rimuovi i campi None dagli IDs
        trakt_movie['ids'] = {k: v for k, v in trakt_movie['ids'].items() if v is not None}

        if formatted_date is not None:
            trakt_movie['watchlisted_at'] = formatted_date
            final_movies.append(trakt_movie)
        if movie_info['watched_at'] is not None:
            trakt_movie['watched_at'] = movie_info['watched_at']
            final_history_movies.append(trakt_movie)
            final_watched_movies.append(trakt_movie)

        print(f"  ✓ {movie.get('title')}")
    else:
        print(f"  ✗ Film non trovato: {imdb_id}")




# Crea il JSON finale nel formato corretto per Trakt sync
trakt_json = {
    'movies': final_movies,
    'shows': final_shows
}
trakt_history_json = {
    'movies': final_history_movies,
    'shows': final_history_shows
}
trakt_watched_json = {
    'movies': final_watched_movies,
    'shows': final_watched_shows
}
# Salva il file
if UPLOAD_ON_TRAKT:
    if not os.path.exists('out/res'):
        os.makedirs('out/res', exist_ok=True)
    response_watchlist = requests.post(url=TRAKT_WATCHLIST_URL,headers=headers, json=trakt_json)
    if response_watchlist.status_code == 200 or response_watchlist.status_code == 201: 
        print('Watchlist importata su Trakt!')
    with open('out/res/watchlist.json', 'w', encoding='utf-8') as f:
        json.dump(response_watchlist.json(), f, indent=2, ensure_ascii=False)
    response_del_history = requests.post(url=TRAKT_HISTORY_URL+'/remove',headers=headers, json=trakt_history_json)
    with open('out/res/history_del.json', 'w', encoding='utf-8') as f:
        json.dump(response_del_history.json(), f, indent=2, ensure_ascii=False)
    if response_del_history.status_code == 200 or response_del_history.status_code == 201:
        print('History ripulita su Trakt...')
        response_history = requests.post(url=TRAKT_HISTORY_URL,headers=headers, json=trakt_history_json)
        if response_history.status_code == 200 or response_history.status_code == 201: 
            print('History importata su Trakt!')
        with open('out/res/history.json', 'w', encoding='utf-8') as f:
            json.dump(response_history.json(), f, indent=2, ensure_ascii=False)
    response_watched = requests.post(url=TRAKT_WATCHED_URL,headers=headers, json=trakt_watched_json)
    if response_watched.status_code == 200 or response_watched.status_code == 201: 
        print('Watched importata su Trakt!')
    with open('out/res/watched.json', 'w', encoding='utf-8') as f:
        json.dump(response_watched.json(), f, indent=2, ensure_ascii=False)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(trakt_json, f, indent=2, ensure_ascii=False)
with open(OUTPUT_HISTORY_FILE, 'w', encoding='utf-8') as f:
    json.dump(trakt_history_json, f, indent=2, ensure_ascii=False)
with open(OUTPUT_WATCHED_FILE, 'w', encoding='utf-8') as f:
    json.dump(trakt_watched_json, f, indent=2, ensure_ascii=False)


total_episodes = sum(
    len(season.get("episodes", []) or [])
    for show in trakt_history_json.get("shows", [])
    if isinstance(show, dict)
    for season in show.get("seasons", []) or []
    if isinstance(season, dict)
)
print(f"\n✅ Salvato {OUTPUT_FILE}")
print(f"   Film: {len(final_movies)}")
print(f"   Serie TV: {len(final_shows)}")
print(f"   Totale stagioni: {sum(len(s['seasons']) for s in trakt_history_json.get("shows", []))}")
print(f"   Totale episodi: {total_episodes}")