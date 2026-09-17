import json
from datetime import datetime
from collections import defaultdict
from utils.generate import generate_primary_json,load_backup
from utils.trakt import get_trakt_watched,get_trakt_info,add_to_trakt_list
import os
import sys
import dotenv
from copy import deepcopy
from pathlib import Path

dotenv.load_dotenv()
DEFAULT_BACKUP_FILE = "in/input.json"
backup_path = Path(os.getenv("NUVIO_BACKUP_FILE", DEFAULT_BACKUP_FILE))
if not backup_path.is_file():
    raise FileNotFoundError(f"Backup Nuvio non trovato: {backup_path}")

library, watched,progress = load_backup(backup_path)
def count_watched_episodes_by_series(watched: list) -> dict:
    """
    Restituisce:
    {
      content_id: {
        "title": str,
        "episodes": set[(season, episode)],
      }
    }
    """
    series = defaultdict(lambda: {"title": "", "episodes": set()})

    for item in watched:
        if item["content_type"] != "series":
            continue

        cid = item["content_id"]
        season = item["season"]
        episode = item["episode"]

        if season is None or episode is None:
            continue

        series[cid]["title"] = item["title"]
        series[cid]["episodes"].add((season, episode))

    return {
        cid: {
            "title": data["title"],
            "watched_count": len(data["episodes"]),
            "episodes": data["episodes"],
        }
        for cid, data in series.items()
    }
def is_show_completed(item: dict) -> bool:
    aired = item["show"].get("aired_episodes", 0)
    seasons = item.get("seasons", [])

    watched_episodes = sum(len(season.get("episodes", [])) for season in seasons)
    print(f"📺 Episodi guardati: {watched_episodes}")
    print(f"📺 Episodi totali: {aired}")
    return watched_episodes >= aired and aired > 0
results_movies = get_trakt_watched("movies")
results_shows = get_trakt_watched("shows")

if results_shows:
    print(f"✅ Caricati {len(results_shows)} serie TV guardate totali\n")
else:
    print(f"⚠️  Nessuna cronologia serie TV trovata")

if results_movies:
    print(f"✅ Caricati {len(results_movies)} film guardati totali\n")
else:
    print(f"⚠️  Nessuna cronologia film trovata")

watched_series = count_watched_episodes_by_series(watched)

for item in results_movies+results_shows:
    imdb_id = item.get('movie',{}).get('ids', {}).get('imdb')
    type = 'movie'
    title = item.get('movie',{}).get('title','')
    completed = True
    if not imdb_id:
        imdb_id = item.get('show',{}).get('ids', {}).get('imdb')
        if not imdb_id:
            continue
        type = 'show'
        title = item.get('show',{}).get('title','')
        aired_count = item.get('show',{}).get('aired_episodes',0)
        found = False
        completed = False
        for cid, info in watched_series.items():
            if cid == imdb_id :
                found=True
                #print(aired_count,info["watched_count"])
                if  info["watched_count"] >= aired_count:
                    completed = True
                    break
        if not completed and found:
            continue
        if not completed and not found:
            print(f"📺 Serie non completata su nuvio: {imdb_id} - {title} - {type} \nVista : {completed} - Found : {found} - Aired : {aired_count}")
            ask = input(f"Vuoi aggiungere {imdb_id} - {title} - {type} alle Gia Viste di trakt? (y/n)")
            if ask.lower() not in ["y","yes"]:
                print("❌ Aggiunta ignorata")
                continue
        #print(f"\n{imdb_id} {title} {type} {completed}")
    
    #print(f"\n{imdb_id} {title} {type} {completed}")

    res = add_to_trakt_list('gia-visti', imdb_id,type)
    print(res)

