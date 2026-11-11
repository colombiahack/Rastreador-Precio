"""Éxito y Olímpica: tiendas sobre VTEX, con API pública de catálogo."""
from typing import List
from urllib.parse import quote

from ..models import Item
from .base import Scraper


class VtexScraper(Scraper):
    base = ""

    def search(self, term: str) -> List[Item]:
        url = (f"{self.base}/api/catalog_system/pub/products/search"
               f"?ft={quote(term)}&_from=0&_to=49")
        out: List[Item] = []
        for p in self.get(url).json():
            try:
                offer = p["items"][0]["sellers"][0]["commertialOffer"]
                price = float(offer.get("Price") or 0)
                if price <= 0 or not offer.get("AvailableQuantity", 1):
                    continue
                lp = float(offer.get("ListPrice") or 0) or None
                out.append(Item(self.name, str(p["productId"]), p["productName"],
                                p.get("link") or self.base, price, lp))
            except (KeyError, IndexError, TypeError, ValueError):
                continue
        return out


class Exito(VtexScraper):
    name = "Éxito"
    base = "https://www.exito.com"


class Olimpica(VtexScraper):
    name = "Olímpica"
    base = "https://www.olimpica.com"
