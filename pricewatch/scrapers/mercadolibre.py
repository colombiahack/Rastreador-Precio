"""Mercado Libre Colombia (sitio MCO) vía su API oficial.

Autenticación (en orden de preferencia):
  1. ML_CLIENT_ID + ML_CLIENT_SECRET: se pide un token (client_credentials) en cada
     ejecución, así nunca caduca. Se crean en developers.mercadolibre.com.co > Mis aplicaciones.
  2. ML_ACCESS_TOKEN: un token ya generado (caduca en horas).

Diagnóstico:  python -m pricewatch.scrapers.mercadolibre "iphone"
"""
import os
import sys
from typing import List, Optional
from urllib.parse import quote

import requests

from ..models import Item
from .base import Scraper

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


class MercadoLibre(Scraper):
    name = "Mercado Libre"

    def _authorize(self) -> None:
        if "Authorization" in self.s.headers:
            return
        cid, secret = os.getenv("ML_CLIENT_ID"), os.getenv("ML_CLIENT_SECRET")
        token: Optional[str] = os.getenv("ML_ACCESS_TOKEN")
        if cid and secret:
            r = self.s.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials",
                      "client_id": cid, "client_secret": secret},
                headers={"accept": "application/json"},
                timeout=20,
            )
            r.raise_for_status()
            token = r.json()["access_token"]
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"

    def search(self, term: str) -> List[Item]:
        self._authorize()
        url = f"https://api.mercadolibre.com/sites/MCO/search?q={quote(term)}&limit=50"
        out: List[Item] = []
        for r in self.get(url).json().get("results", []):
            price = r.get("price")
            if not price:
                continue
            out.append(Item(self.name, r["id"], r["title"], r["permalink"],
                            float(price), r.get("original_price")))
        return out


if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "iphone"
    try:
        items = MercadoLibre().search(term)
    except requests.RequestException as e:
        print(f"Error: {e}")
        if getattr(e, "response", None) is not None:
            print(e.response.text[:300])
        sys.exit(1)
    print(f"{len(items)} productos")
    for i in items[:3]:
        print(f"- {i.name[:60]} | ${i.price:,.0f} | {i.url}")
