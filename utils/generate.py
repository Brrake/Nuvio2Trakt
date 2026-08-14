"""Generate Trakt-compatible intermediate JSON files from a Nuvio backup."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BACKUP_FILE = "in/input.json"
WATCHLIST_OUTPUT = Path("out/trakt_watchlist.json")
HISTORY_OUTPUT = Path("out/trakt_history.json")


def utc_iso(milliseconds: int | float | None) -> str | None:
    """Convert a Unix timestamp in milliseconds to a UTC ISO-8601 string."""
    if milliseconds is None:
        return None

    try:
        timestamp = float(milliseconds) / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def load_backup(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load and validate the library and watched collections from a backup."""
    with path.open("r", encoding="utf-8") as backup_file:
        payload = json.load(backup_file)

    original = payload.get("original", {})
    library = original.get("library", [])
    watched = original.get("watched", [])

    if not isinstance(library, list) or not isinstance(watched, list):
        raise ValueError("Il backup deve contenere original.library e original.watched come liste")

    return library, watched


def write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    """Write JSON output, creating its parent directory when necessary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")


def generate_primary_json() -> None:
    """Generate watchlist and history files consumed by the sync script."""
    backup_path = Path(os.getenv("NUVIO_BACKUP_FILE", DEFAULT_BACKUP_FILE))
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup Nuvio non trovato: {backup_path}")

    library, watched = load_backup(backup_path)

    watched_by_content: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in watched:
        content_id = item.get("content_id")
        if content_id:
            watched_by_content[content_id].append(item)

    watchlist: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    skipped = 0

    for library_item in library:
        content_id = library_item.get("content_id")
        content_type = library_item.get("content_type")
        watchlisted_at = utc_iso(library_item.get("added_at"))

        if not content_id or not watchlisted_at:
            skipped += 1
            continue

        watched_items = watched_by_content.get(content_id, [])

        if content_type == "series":
            watchlist.append(
                {
                    "imdb_id": content_id,
                    "type": "show",
                    "watchlisted_at": watchlisted_at,
                }
            )
        elif content_type == "movie":
            if len(watched_items) == 1:
                watched_at = utc_iso(watched_items[0].get("watched_at"))
                if watched_at:
                    history.append(
                        {
                            "imdb_id": content_id,
                            "type": "movie",
                            "watched_at": watched_at,
                        }
                    )
                else:
                    watchlist.append(
                        {
                            "imdb_id": content_id,
                            "type": "movie",
                            "watchlisted_at": watchlisted_at,
                        }
                    )
            else:
                watchlist.append(
                    {
                        "imdb_id": content_id,
                        "type": "movie",
                        "watchlisted_at": watchlisted_at,
                    }
                )
        else:
            skipped += 1
            continue

        for episode in watched_items:
            watched_at = utc_iso(episode.get("watched_at"))
            season = episode.get("season")
            episode_number = episode.get("episode")

            if (
                content_type == "series"
                and watched_at
                and season is not None
                and episode_number is not None
            ):
                history.append(
                    {
                        "imdb_id": content_id,
                        "type": "episode",
                        "season": season,
                        "episode": episode_number,
                        "watched_at": watched_at,
                    }
                )

    write_json(WATCHLIST_OUTPUT, watchlist)
    write_json(HISTORY_OUTPUT, history)

    print(f"📦 Watchlist: {len(watchlist)} elementi")
    print(f"🕘 History: {len(history)} elementi")
    if skipped:
        print(f"⚠️ Elementi ignorati: {skipped}")


if __name__ == "__main__":
    generate_primary_json()
