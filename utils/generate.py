import json
from datetime import datetime, timezone
import dotenv
import os
dotenv.load_dotenv()
def generate_primary_json():
    watchlist = []
    history = []

    bk_path = os.getenv("NUVIO_BACKUP_FILE", "")

    with open(bk_path, encoding='utf-8') as data:
        parsed = json.load(data)
        library = parsed['original']['library']
        watched = parsed['original']['watched']

    for lib in library:
        dt = datetime.fromtimestamp(lib['added_at'] / 1000, tz=timezone.utc)
        watchlisted_at = dt.strftime('%Y-%m-%dT%H:%M:%SZ')  # Formato ISO corretto
        
        if lib['content_type'] == 'series':
            content_type = 'show'
        else:
            content_type = lib['content_type']
        
        # Cerca se è stato visto
        risultati = [item for item in watched if item.get('content_id') == lib['content_id']]
        
        if content_type == 'movie' and len(risultati) == 1:
            # Film già visto → HISTORY
            dt_wa = datetime.fromtimestamp(risultati[0]['watched_at'] / 1000, tz=timezone.utc)
            watched_at = dt_wa.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            history.append({
                "imdb_id": lib['content_id'],
                "type": "movie",
                "watched_at": watched_at
            })
        elif content_type == 'show':
            # Serie TV → WATCHLIST (solo la serie, non gli episodi)
            watchlist.append({
                "imdb_id": lib['content_id'],
                "type": "show",
                "watchlisted_at": watchlisted_at
            })
            
            # Aggiungi gli episodi visti alla HISTORY
            for ep in risultati:
                dt_wa_ep = datetime.fromtimestamp(ep['watched_at'] / 1000, tz=timezone.utc)
                watched_at_ep = dt_wa_ep.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                history.append({
                    "imdb_id": ep['content_id'],
                    "type": "episode",
                    "season": ep['season'],
                    "episode": ep['episode'],
                    "watched_at": watched_at_ep
                })
        else:
            # Film non visto → WATCHLIST
            watchlist.append({
                "imdb_id": lib['content_id'],
                "type": "movie",
                "watchlisted_at": watchlisted_at
            })

    # Salva due file separati
    #shows = [wl for wl in watchlist if wl['type'] == 'show']
    #with open('out/trakt_watchlist_shows.json', 'w', encoding='utf-8') as f:
    #    json.dump(shows, f, indent=2)
    with open('out/trakt_watchlist.json', 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, indent=2)

    with open('out/trakt_history.json', 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

    print(f"Watchlist: {len(watchlist)} elementi")
    print(f"History: {len(history)} elementi")