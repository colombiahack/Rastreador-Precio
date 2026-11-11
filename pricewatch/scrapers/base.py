import re
import time
from typing import List, Optional

import requests

from ..models import Item

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def parse_cop(value) -> Optional[float]:
    """'1.299.900', '$ 1.299.900,00', 1299900 -> 1299900.0"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = re.sub(r"[^\d.,]", "", str(value))
    if not s:
        return None
    if "," in s and "." in s:          # 1.299.900,00
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:                      # 1299900,50 o 1,299,900
        parts = s.split(",")
        s = s.replace(",", "") if len(parts[-1]) == 3 else s.replace(",", ".")
    elif s.count(".") > 0 and len(s.split(".")[-1]) == 3:   # 1.299.900
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


class Scraper:
    name = "base"
    delay = 1.5  # segundos entre peticiones: sé amable con los sitios

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "es-CO,es;q=0.9"})

    def get(self, url: str, **kw) -> requests.Response:
        time.sleep(self.delay)
        r = self.s.get(url, timeout=20, **kw)
        r.raise_for_status()
        return r

    def search(self, term: str) -> List[Item]:
        raise NotImplementedError
