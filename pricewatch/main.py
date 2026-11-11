"""Ciclo principal: rastrea, detecta y avisa.

Uso:
  python -m pricewatch.main            # un ciclo y termina (ideal para cron / Actions)
  python -m pricewatch.main --loop 60  # repite cada 60 s
  python -m pricewatch.main --dry-run  # no envía a Telegram, imprime
"""
import argparse
import concurrent.futures as cf
import json
import os
import time

import requests

from . import notifier
from .db import DB
from .detector import detect
from .scrapers import SCRAPERS


def load_watchlist(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def scrape_store(key: str, terms: list):
    scraper = SCRAPERS[key]()
    items = []
    for t in terms:
        try:
            items.extend(scraper.search(t))
        except (requests.RequestException, ValueError) as e:
            print(f"[{key}] '{t}': {e}")
    return key, items


def run_cycle(db: DB, watchlist: dict, dry_run: bool) -> int:
    if not dry_run and os.getenv("TELEGRAM_BOT_TOKEN"):
        notifier.poll_commands(db)

    stores = {k: v for k, v in watchlist.items() if k in SCRAPERS}
    found = 0
    with cf.ThreadPoolExecutor(max_workers=len(stores) or 1) as pool:
        for key, items in pool.map(lambda kv: scrape_store(*kv), stores.items()):
            print(f"[{key}] {len(items)} productos")
            for item in items:
                base = db.baseline(item.store, item.sku)   # ANTES de guardar el precio nuevo
                glitch = detect(item, base)
                db.save(item)
                if glitch and not db.already_alerted(item):
                    found += 1
                    db.mark_alerted(item)
                    if dry_run:
                        print(notifier.format_glitch(glitch), "\n")
                    else:
                        notifier.broadcast(db.subscribers(), glitch)
    db.commit()
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchlist", default="watchlist.json")
    ap.add_argument("--db", default=os.getenv("DB_PATH", "pricewatch.db"))
    ap.add_argument("--loop", type=int, default=0, help="segundos entre ciclos (0 = una vez)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    db = DB(a.db)
    while True:
        n = run_cycle(db, load_watchlist(a.watchlist), a.dry_run)
        print(f"Ciclo listo: {n} alertas")
        if not a.loop:
            break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
