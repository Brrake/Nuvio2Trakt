import json
from datetime import datetime
from collections import defaultdict
from utils.generate import generate_primary_json
from utils.trakt import add_to_trakt_history,add_to_trakt_watchlist,delete_from_trakt_history,get_trakt_info
import os
import dotenv
from copy import deepcopy
from pathlib import Path

dotenv.load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# 🔧 Configurazione
# ─────────────────────────────────────────────────────────────────────────────
UPLOAD_ON_TRAKT = os.getenv("UPLOAD_ON_TRAKT", "false") == "true"
DEBUG = os.getenv("DEBUG", "false") == "true"
CLEAN_OLD_HISTORY = os.getenv("CLEAN_OLD_HISTORY", "false") == "true"

OUTPUT_FILE = "out/sync/trakt_sync.json"
OUTPUT_HISTORY_FILE = "out/sync/trakt_history_sync.json"
OUTPUT_WATCHED_FILE = "out/sync/trakt_watched_sync.json"

output_dir = os.path.dirname(OUTPUT_FILE)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)



# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Avvio
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("🎬  TRAKT SYNC - Sincronizzazione Watchlist & History")
print("="*60 + "\n")

print("📦 Generazione dati primari...")
generate_primary_json()
print("✅ Dati primari generati\n")

# ─────────────────────────────────────────────────────────────────────────────
# 📥 Caricamento dati
# ─────────────────────────────────────────────────────────────────────────────
print("📂 Caricamento dati da file...")
with open('out/trakt_watchlist.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
with open('out/trakt_history.json', 'r', encoding='utf-8') as f2:
    data += json.load(f2)
print(f"✅ Caricati {len(data)} elementi totali\n")

# ─────────────────────────────────────────────────────────────────────────────
# 🗂️ Strutture dati
# ─────────────────────────────────────────────────────────────────────────────
shows_data = defaultdict(lambda: {
    'imdb_id': None,
    'seasons': defaultdict(lambda: defaultdict(list)),
    'watchlisted_at': None,
    'watched_at': None
})

movies_data = defaultdict(lambda: {
    'imdb_id': None,
    'watchlisted_at': None,
    'watched_at': None
})

# ─────────────────────────────────────────────────────────────────────────────
# 📊 Processamento elementi
# ─────────────────────────────────────────────────────────────────────────────
print("🔄 Processamento elementi...")
episode_count = 0
movie_count = 0
show_count = 0
skipped_count = 0

for item in data:
    imdb_id = item.get('imdb_id')
    if not imdb_id:
        skipped_count += 1
        continue
    
    watchlisted_at = item.get('watchlisted_at')
    watched_at = item.get('watched_at')
    
    if item['type'] == 'episode':
        season = item.get('season')
        episode = item.get('episode')
        
        if season is None or episode is None:
            skipped_count += 1
            continue
        
        shows_data[imdb_id]['seasons'][season][episode] = watched_at
        episode_count += 1
        
    elif item['type'] == 'movie':
        movies_data[imdb_id]['imdb_id'] = imdb_id
        if watchlisted_at:
            movies_data[imdb_id]['watchlisted_at'] = watchlisted_at
        if watched_at:
            movies_data[imdb_id]['watched_at'] = watched_at
        movie_count += 1
        
    else:
        shows_data[imdb_id]['imdb_id'] = imdb_id
        shows_data[imdb_id]['watchlisted_at'] = watchlisted_at
        show_count += 1

print(f"✅ Processati: {episode_count} episodi, {movie_count} film, {show_count} serie")
if skipped_count > 0:
    print(f"⚠️  Saltati {skipped_count} elementi incompleti\n")

# ─────────────────────────────────────────────────────────────────────────────
# 🐛 Debug mode
# ─────────────────────────────────────────────────────────────────────────────
if DEBUG:
    print("🐛 Modalitàī° DEBUG attiva - salvataggio dati intermedi...")
    DEBUG_DIR = Path("debug")
    DEBUG_DIR.mkdir(exist_ok=True)
    with open('debug/shows_data.json', 'w', encoding='utf-8') as f:
        json.dump(shows_data, f, indent=2, ensure_ascii=False)
    with open('debug/movies_data.json', 'w', encoding='utf-8') as f:
        json.dump(movies_data, f, indent=2, ensure_ascii=False)
    print("✅ File debug salvati\n")

# ─────────────────────────────────────────────────────────────────────────────
# 📺 Processamento Serie TV
# ─────────────────────────────────────────────────────────────────────────────
final_shows = []
final_movies = []

final_history_shows = []
final_history_movies = []

print("\n" + "─"*60)
print("📺  ELABORAZIONE SERIE TV")
print("─"*60)

shows_processed = 0
shows_found = 0
shows_not_found = 0

for imdb_id, show_info in shows_data.items():
    shows_processed += 1
    print(f"\n[{shows_processed}/{len(shows_data)}] 📺 Processing show {imdb_id}...")
    
    results = get_trakt_info(imdb_id, 'show')
    
    if results and len(results) > 0:
        shows_found += 1
        show = results[0].get('show', {})
        show_episodes = show.get('aired_episodes', 0)
        show_ids = show.get('ids', {})
        show_title = show.get('title', 'Unknown')
        
        try:
            dt = datetime.fromisoformat(show_info['watchlisted_at'].replace('+00:00', 'Z'))
            formatted_date = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except Exception:
            formatted_date = show_info.get('watchlisted_at', '')
        
        trakt_show = {
            'title': show_title,
            'year': show.get('year', 0),
            'ids': {
                'tvdb': show_ids.get('tvdb'),
                'imdb': imdb_id,
                'tmdb': show_ids.get('tmdb'),
                'trakt': show_ids.get('trakt')
            },
            'seasons': []
        }
        
        # Rimuovi campi None dagli IDs
        trakt_show['ids'] = {k: v for k, v in trakt_show['ids'].items() if v is not None}
        
        # Costruisci stagioni ed episodi
        for season_num, episodes in sorted(
            ((s, eps) for s, eps in show_info['seasons'].items() if s is not None),
            key=lambda x: x[0]
        ):
            season_obj = {
                'number': season_num,
                'episodes': []
            }
            
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

        
        out = deepcopy(trakt_show)
        out.pop("seasons", None)
        if formatted_date:
            out['watchlisted_at'] = formatted_date
        if len(trakt_show['seasons']) > 0:
            out['watched_at'] = trakt_show['seasons'][-1]['episodes'][-1]['watched_at']
        if out.get('watched_at',''):
            final_history_shows.append(trakt_show)
        else : final_shows.append(out)


        season_count = len(show_info['seasons'])
        print(f"  ✅ {show_title} - {season_count} stagione/i - {show_episodes} episodi")
    else:
        shows_not_found += 1
        print(f"  ❌ Serie non trovata: {imdb_id}")

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 Processamento Film
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "─"*60)
print("🎬  ELABORAZIONE FILM")
print("─"*60)

movies_processed = 0
movies_found = 0
movies_not_found = 0

for imdb_id, movie_info in movies_data.items():
    movies_processed += 1
    print(f"\n[{movies_processed}/{len(movies_data)}] 🎬 Processing movie {imdb_id}...")
    
    results = get_trakt_info(imdb_id, 'movie')
    
    if results and len(results) > 0:
        movies_found += 1
        movie = results[0].get('movie', {})
        movie_ids = movie.get('ids', {})
        movie_title = movie.get('title', 'Unknown')
        
        try:
            dt = datetime.fromisoformat(movie_info['watchlisted_at'].replace('+00:00', 'Z'))
            formatted_date = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except Exception:
            formatted_date = movie_info.get('watchlisted_at', '')
        
        trakt_movie = {
            'title': movie_title,
            'year': movie.get('year', 0),
            'ids': {
                'tvdb': movie_ids.get('tvdb'),
                'imdb': imdb_id,
                'tmdb': movie_ids.get('tmdb'),
                'trakt': movie_ids.get('trakt')
            }
        }
        
        # Rimuovi campi None dagli IDs
        trakt_movie['ids'] = {k: v for k, v in trakt_movie['ids'].items() if v is not None}
        
        if formatted_date:
            trakt_movie['watchlisted_at'] = formatted_date
            final_movies.append(trakt_movie)
        
        if movie_info.get('watched_at'):
            trakt_movie['watched_at'] = movie_info['watched_at']
            final_history_movies.append(trakt_movie)
        
        print(f"  ✅ {movie_title}")
    else:
        movies_not_found += 1
        print(f"  ❌ Film non trovato: {imdb_id}")

# ─────────────────────────────────────────────────────────────────────────────
# 📦 Creazione JSON finale
# ─────────────────────────────────────────────────────────────────────────────
trakt_json = {
    'movies': final_movies,
    'shows': final_shows
}
trakt_history_json = {
    'movies': final_history_movies,
    'shows': final_history_shows
}

# ─────────────────────────────────────────────────────────────────────────────
# ☁️ Upload su Trakt (opzionale)
# ─────────────────────────────────────────────────────────────────────────────
if UPLOAD_ON_TRAKT:
    print("\n" + "─"*60)
    print("☁️  UPLOAD SU TRAKT")
    print("─"*60)
    
    # Watchlist
    add_to_trakt_watchlist(trakt_json)
    # History - rimozione
    if CLEAN_OLD_HISTORY:
        delete_from_trakt_history(trakt_history_json)
        add_to_trakt_history(trakt_history_json)
    else:
        # History - inserimento
        add_to_trakt_history(trakt_history_json)

# ─────────────────────────────────────────────────────────────────────────────
# 💾 Salvataggio file
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "─"*60)
print("💾  SALVATAGGIO FILE")
print("─"*60)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(trakt_json, f, indent=2, ensure_ascii=False)
print(f"  ✅ {OUTPUT_FILE}")

with open(OUTPUT_HISTORY_FILE, 'w', encoding='utf-8') as f:
    json.dump(trakt_history_json, f, indent=2, ensure_ascii=False)
print(f"  ✅ {OUTPUT_HISTORY_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# 📊 Riepilogo finale
# ─────────────────────────────────────────────────────────────────────────────
total_episodes = sum(
    len(season.get("episodes", []) or [])
    for show in trakt_history_json.get("shows", [])
    if isinstance(show, dict)
    for season in show.get("seasons", []) or []
    if isinstance(season, dict)
)

total_seasons = sum(
    len(show.get('seasons', []) or [])
    for show in trakt_history_json.get("shows", [])
    if isinstance(show, dict)
)

print("\n" + "="*60)
print("📊  RIEPILOGO FINALE")
print("="*60)
print(f"\n✅ Operazione completata con successo!")
print(f"\n📦 Dati elaborati:")
print(f"   • Film in watchlist: {len(final_movies)}")
print(f"   • Serie TV in watchlist: {len(final_shows)}")
print(f"   • Film in history: {len(final_history_movies)}")
print(f"   • Serie TV in history: {len(final_history_shows)}")
print(f"\n📺 Dettagli serie TV:")
print(f"   • Totale stagioni: {total_seasons}")
print(f"   • Totale episodi: {total_episodes}")

if DEBUG:
    print(f"\n🐛 Debug: file intermedi salvati in ./debug/")

if UPLOAD_ON_TRAKT:
    print(f"\n☁️  Upload: dati inviati a Trakt API")
    print(f"   • Risposte salvate in ./out/res/")

print(f"\n💾 Output:")
print(f"   • {OUTPUT_FILE}")
print(f"   • {OUTPUT_HISTORY_FILE}")
print(f"   • {OUTPUT_WATCHED_FILE}")
print("\n" + "="*60 + "\n")