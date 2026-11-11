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

NAME_KEYS = ["name", "title", "productname", "label"]
SELL_KEYS = ["discountprice", "sellingprice", "saleprice", "finalprice", "currentprice",
             "pricevalue"]
LIST_KEYS = ["price", "listprice", "oldprice", "baseprice", "regularprice", "strikeprice",
             "originalprice", "pricebeforediscount"]
URL_KEYS = ["url_es", "url", "producturl", "path", "link", "slug"]
ID_KEYS = ["code", "sku", "objectid", "id"]

# Algolia suele nombrar campos como name_text_es, code_string, discountprice_double...
TYPE_SUFFIX = re.compile(r"_(double|string|int|long|boolean|text_es|text)(_mv)?$")


def _norm(key: str) -> str:
    return TYPE_SUFFIX.sub("", key.lower())


def _pick(node: Any, keys: List[str], depth: int = 0) -> Any:
    """Primer valor escalar cuya clave (sin mayúsculas) esté en keys; busca en anidados."""
    if depth > 4:
        return None
    if isinstance(node, dict):
        low = {_norm(k): v for k, v in node.items() if not k.startswith("_")}
        for k in keys:
            v = low.get(k)
            if isinstance(v, dict):
                v = _pick(v, ["value", "amount", "pricevalue", "formattedvalue"], depth + 1)
            if isinstance(v, list) and v:
                v = v[0]
            if v not in (None, "", {}, []):
                return v
        for k, v in node.items():
            if not k.startswith("_") and isinstance(v, (dict, list)):
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
        sell = parse_cop(_pick(hit, SELL_KEYS))
        listed = [v for v in (parse_cop(_pick(hit, [k])) for k in LIST_KEYS) if v]
        price = sell or (listed[0] if listed else None)
        name = _pick(hit, NAME_KEYS)
        if not price or not name:
            return None
        top = max(listed) if listed else None
        list_price = top if (top and top > price) else None
        sku = str(_pick(hit, ID_KEYS) or name)
        url = _pick(hit, URL_KEYS)
        if not url:
            url = f"{self.base}/search?text={sku}"
        url = str(url)
        if url.startswith("/"):
            url = self.base + url
        return Item(self.name, sku, str(name), url, price, list_price)

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
        useful = re.compile(r"price|disc|name|url|code|link|slug|path|list|base|stock", re.I)
        brief = {k: str(v)[:70] for k, v in hits[0].items()
                 if not k.startswith("_") and useful.search(k)}
        print(json.dumps(brief, ensure_ascii=False, indent=0))

