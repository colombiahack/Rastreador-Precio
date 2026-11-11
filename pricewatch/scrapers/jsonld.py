"""Alkosto y Ktronix (mismo grupo): extracción genérica desde JSON-LD / microdatos.

Es el punto menos verificado: las páginas de búsqueda pueden cargar los productos por
JavaScript. Si search() devuelve vacío, abre la búsqueda en el navegador, mira en
DevTools > Network la petición JSON de productos y reemplaza este scraper por esa API.
"""
import json
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Item
from .base import Scraper, parse_cop


def _products(node):
    if isinstance(node, dict):
        if node.get("@type") == "Product":
            yield node
        for v in node.values():
            yield from _products(v)
    elif isinstance(node, list):
        for v in node:
            yield from _products(v)


class JsonLdScraper(Scraper):
    base = ""
    search_path = "/search?text="

    def search(self, term: str) -> List[Item]:
        url = f"{self.base}{self.search_path}{quote(term)}"
        soup = BeautifulSoup(self.get(url).text, "html.parser")
        out: List[Item] = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except json.JSONDecodeError:
                continue
            for p in _products(data):
                offers = p.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price = parse_cop(offers.get("price") or offers.get("lowPrice"))
                if not price:
                    continue
                url_p = p.get("url") or offers.get("url") or self.base
                if url_p.startswith("/"):
                    url_p = self.base + url_p
                out.append(Item(self.name, str(p.get("sku") or url_p), p.get("name", ""),
                                url_p, price, None))
        return out


class Alkosto(JsonLdScraper):
    name = "Alkosto"
    base = "https://www.alkosto.com"


class Ktronix(JsonLdScraper):
    name = "Ktronix"
    base = "https://www.ktronix.com"
