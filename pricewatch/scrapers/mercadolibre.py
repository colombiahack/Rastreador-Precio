"""Mercado Libre Colombia (sitio MCO) vía su API oficial.

Si la búsqueda responde 401/403, crea una app en developers.mercadolibre.com.co
y define ML_ACCESS_TOKEN (Bearer).
"""
import os
from typing import List
from urllib.parse import quote

from ..models import Item
from .base import Scraper


class MercadoLibre(Scraper):
    name = "Mercado Libre"

    def search(self, term: str) -> List[Item]:
        token = os.getenv("ML_ACCESS_TOKEN")
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"
        url = f"https://api.mercadolibre.com/sites/MCO/search?q={quote(term)}&limit=50"
        out: List[Item] = []
        for r in self.get(url).json().get("results", []):
            price = r.get("price")
            if not price:
                continue
            out.append(Item(self.name, r["id"], r["title"], r["permalink"],
                            float(price), r.get("original_price")))
        return out
