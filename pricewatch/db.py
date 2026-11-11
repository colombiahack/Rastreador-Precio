import sqlite3
import statistics
import time
from typing import List, Optional

from .models import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
  store TEXT, sku TEXT, name TEXT, url TEXT,
  price REAL, list_price REAL, ts INTEGER
);
CREATE INDEX IF NOT EXISTS idx_prices ON prices(store, sku, ts);
CREATE TABLE IF NOT EXISTS alerts (
  store TEXT, sku TEXT, price REAL, ts INTEGER,
  PRIMARY KEY (store, sku, price)
);
CREATE TABLE IF NOT EXISTS subscribers (chat_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
"""


class DB:
    def __init__(self, path: str = "pricewatch.db"):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    # --- historial de precios ---
    def history(self, store: str, sku: str, limit: int = 30) -> List[float]:
        rows = self.conn.execute(
            "SELECT price FROM prices WHERE store=? AND sku=? ORDER BY ts DESC LIMIT ?",
            (store, sku, limit),
        ).fetchall()
        return [r[0] for r in rows]

    def baseline(self, store: str, sku: str) -> Optional[float]:
        """Mediana del historial reciente; None si hay menos de 3 observaciones."""
        h = self.history(store, sku)
        return statistics.median(h) if len(h) >= 3 else None

    def save(self, item: Item) -> None:
        self.conn.execute(
            "INSERT INTO prices VALUES (?,?,?,?,?,?,?)",
            (item.store, item.sku, item.name, item.url, item.price,
             item.list_price, int(time.time())),
        )

    # --- alertas (deduplicación) ---
    def already_alerted(self, item: Item) -> bool:
        r = self.conn.execute(
            "SELECT 1 FROM alerts WHERE store=? AND sku=? AND price=?",
            (item.store, item.sku, item.price),
        ).fetchone()
        return r is not None

    def mark_alerted(self, item: Item) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO alerts VALUES (?,?,?,?)",
            (item.store, item.sku, item.price, int(time.time())),
        )

    # --- suscriptores de Telegram ---
    def add_subscriber(self, chat_id: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO subscribers VALUES (?)", (str(chat_id),))

    def remove_subscriber(self, chat_id: str) -> None:
        self.conn.execute("DELETE FROM subscribers WHERE chat_id=?", (str(chat_id),))

    def subscribers(self) -> List[str]:
        return [r[0] for r in self.conn.execute("SELECT chat_id FROM subscribers")]

    def get_kv(self, k: str, default: str = "") -> str:
        r = self.conn.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return r[0] if r else default

    def set_kv(self, k: str, v: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, v))

    def commit(self) -> None:
        self.conn.commit()
