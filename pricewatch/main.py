"""Ciclo principal: rastrea tienda por tienda, avisa del progreso y de las alertas.

Uso:
  python -m pricewatch.main            # un ciclo y termina
  python -m pricewatch.main --loop 300 # repite cada 300 s
  python -m pricewatch.main --dry-run  # no envía a Telegram, imprime

PROGRESS (variable de entorno): first (por defecto, avisos de progreso solo en la
primera ronda), all (en todas las rondas) u off (nunca).
"""
import argparse
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
    """Devuelve (items, n_errores) para una tienda."""
    scraper = SCRAPERS[key]()
    items, errors = [], 0
    for t in terms:
        try:
            items.extend(scraper.search(t))
        except (requests.RequestException, ValueError) as e:
            errors += 1
            print(f"[{key}] '{t}': {e}")
    return items, errors


def say(db: DB, text: str, dry_run: bool, enabled: bool = True) -> None:
    """Muestra el mensaje en consola y, si corresponde, lo manda a los suscriptores."""
    print(text)
    if not enabled or dry_run or not os.getenv("TELEGRAM_BOT_TOKEN"):
        return
    for cid in db.subscribers():
        try:
            notifier.send(cid, text)
        except requests.RequestException as e:
            print(f"[telegram] fallo enviando a {cid}: {e}")


def poll(db: DB, dry_run: bool) -> None:
    if dry_run or not os.getenv("TELEGRAM_BOT_TOKEN"):
        return
    try:
        notifier.poll_commands(db)   # atiende /start y /stop
    except requests.RequestException as e:
        print(f"[telegram] no pude leer comandos: {e}")


def run_cycle(db: DB, watchlist: dict, dry_run: bool, announce: bool = True) -> int:
    stores = {k: v for k, v in watchlist.items() if k in SCRAPERS}
    total = 0
    for key, terms in stores.items():
        name = SCRAPERS[key].name
        poll(db, dry_run)  # así /start se responde entre tienda y tienda
        say(db, f"🔎 Estoy revisando {name}…", dry_run, announce)

        items, errors = scrape_store(key, terms)
        found = 0
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
        total += found

        if not items:
            say(db, f"⚠️ {name}: no encontré productos "
                    f"({errors} búsquedas con error). Sigo con la siguiente.",
                dry_run, announce)
        else:
            say(db, f"✅ {name}: {len(items)} productos, {found} alertas.",
                dry_run, announce)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchlist", default="watchlist.json")
    ap.add_argument("--db", default=os.getenv("DB_PATH", "pricewatch.db"))
    ap.add_argument("--loop", type=int, default=0, help="segundos entre ciclos (0 = una vez)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    mode = os.getenv("PROGRESS", "first").lower()
    db = DB(a.db)
    first = True
    while True:
        announce = mode == "all" or (mode == "first" and first)
        n = run_cycle(db, load_watchlist(a.watchlist), a.dry_run, announce)
        say(db, f"Ronda lista: {n} alertas."
                + (f" Próxima ronda en {a.loop // 60} min." if a.loop else ""),
            a.dry_run, announce)
        first = False
        if not a.loop:
            break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()
