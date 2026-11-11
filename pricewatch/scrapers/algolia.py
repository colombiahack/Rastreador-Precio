
"""Alkosto y Ktronix: su buscador es Algolia.

La página de búsqueda trae el applicationId, la clave de SOLO búsqueda (pública: la usa
el navegador de cualquier visitante) y el nombre del índice. Se leen de la página en cada
ejecución; no se guardan en el repositorio.

Los campos exactos de cada registro (hit) no se verificaron: _pick() busca nombres
habituales. Diagnóstico:  python -m pricewatch.scrapers.algolia alkosto televisor
"""
import json
import re
import sys
from typing import Any, List, Optional

from ..models import Item
from .base import Scraper, parse_cop

APP_RE = re.compile(r"applicationId[\"']?\s*:\s*[\"']([A-Za-z0-9]+)[\"']")
KEY_RE = re.compile(r"(?<![A-Za-z])apiKey[\"']?\s*:\s*[\"']([A-Za-z0-9=+/_-]{20,})[\"']")
IDX_RE = re.compile(r"indexName[\"']?\s*:\s*[\"']([^\"']+)[\"']")

NAME_KEYS = ["name", "title", "productname", "label", "description"]
PRICE_KEYS = ["price", "pricevalue", "sellingprice", "finalprice", "saleprice", "currentprice"]
LIST_KEYS = ["listprice", "oldprice", "baseprice", "regularprice", "strikeprice",
             "priceoriginal", "originalprice", "pricebeforediscount"]
URL_KEYS = ["url", "path", "link", "producturl"]
ID_KEYS = ["code", "sku", "objectid", "id"]


def _pick(node: Any, keys: List[str], depth: int = 0) -> Any:
    """Primer valor escalar cuya clave (sin mayúsculas) esté en keys; busca en anidados."""
    if depth > 4:
        return None
    if isinstance(node, dict):
        low = {k.lower(): v for k, v in node.items()}
        for k in keys:
            v = low.get(k)
            if isinstance(v, dict):
                v = _pick(v, ["value", "amount", "pricevalue", "formattedvalue"], depth + 1)
            if isinstance(v, list) and v:
                v = v[0]
            if v not in (None, "", {}, []):
                return v
        for v in node.values():
            if isinstance(v, (dict, list)):
                found = _pick(v, keys, depth + 1)
                if found is not None:
                    return found
    elif isinstance(node, list):
        for v in node[:3]:
            found = _pick(v, keys, depth + 1)
            if found is not None:
                return found
    return None


class AlgoliaStore(Scraper):
    base = ""
    page = "/search?text=televisor"
    hits_per_page = 50

    def __init__(self):
        super().__init__()
        self._cfg: Optional[tuple] = None

    def _config(self) -> tuple:
        if not self._cfg:
            html = self.get(self.base + self.page).text
            app, key, idx = APP_RE.search(html), KEY_RE.search(html), IDX_RE.search(html)
            if not (app and key and idx):
                raise ValueError(f"{self.name}: no encontré la configuración de Algolia")
            self._cfg = (app.group(1), key.group(1), idx.group(1))
        return self._cfg

    def raw_hits(self, term: str) -> List[dict]:
        app, key, idx = self._config()
        r = self.s.post(
            f"https://{app}-dsn.algolia.net/1/indexes/{idx}/query",
            headers={"X-Algolia-Application-Id": app, "X-Algolia-API-Key": key},
            json={"query": term, "hitsPerPage": self.hits_per_page},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("hits", [])

    def to_item(self, hit: dict) -> Optional[Item]:
        price = parse_cop(_pick(hit, PRICE_KEYS))
        name = _pick(hit, NAME_KEYS)
        if not price or not name:
            return None
        sku = str(_pick(hit, ID_KEYS) or name)
        url = str(_pick(hit, URL_KEYS) or self.base)
        if url.startswith("/"):
            url = self.base + url
        return Item(self.name, sku, str(name), url, price, parse_cop(_pick(hit, LIST_KEYS)))

    def search(self, term: str) -> List[Item]:
        items = (self.to_item(h) for h in self.raw_hits(term))
        return [i for i in items if i]


class Alkosto(AlgoliaStore):
    name = "Alkosto"
    base = "https://www.alkosto.com"


class Ktronix(AlgoliaStore):
    name = "Ktronix"
    base = "https://www.ktronix.com"


if __name__ == "__main__":
    which = {"alkosto": Alkosto, "ktronix": Ktronix}
    store = which[sys.argv[1]]()
    term = sys.argv[2] if len(sys.argv) > 2 else "televisor"
    hits = store.raw_hits(term)
    print(f"{len(hits)} hits; con precio y nombre reconocidos: {len(store.search(term))}")
    if hits:
        print(json.dumps(hits[0], ensure_ascii=False)[:1500])
