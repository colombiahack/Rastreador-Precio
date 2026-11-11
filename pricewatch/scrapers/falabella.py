"""Falabella Colombia: lee el JSON embebido (__NEXT_DATA__) de la página de búsqueda.

La estructura puede cambiar; si no devuelve resultados, inspecciona el JSON y ajusta
_find_results(). Falabella tiene protección anti-bots: puede requerir proxy residencial.
"""
import json
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Item
from .base import Scraper, parse_cop


def _find_results(node):
    """Busca recursivamente la primera lista 'results' de productos."""
    if isinstance(node, dict):
        r = node.get("results")
        if isinstance(r, list) and r and isinstance(r[0], dict) and "prices" in r[0]:
            return r
        for v in node.values():
            found = _find_results(v)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_results(v)
            if found:
                return found
    return None


class Falabella(Scraper):
    name = "Falabella"

    def search(self, term: str) -> List[Item]:
        url = f"https://www.falabella.com.co/falabella-co/search?Ntt={quote(term)}"
        soup = BeautifulSoup(self.get(url).text, "html.parser")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag or not tag.string:
            return []
        results = _find_results(json.loads(tag.string)) or []
        out: List[Item] = []
        for r in results:
            cur = lst = None
            for p in r.get("prices", []):
                val = parse_cop((p.get("price") or [None])[0])
                if p.get("type") in ("internetPrice", "eventPrice") and val:
                    cur = min(cur, val) if cur else val
                elif p.get("type") == "normalPrice":
                    lst = val
            if cur:
                out.append(Item(self.name, str(r.get("skuId") or r.get("productId")),
                                r.get("displayName", ""), r.get("url", url), cur, lst))
        return out
