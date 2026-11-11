from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    store: str
    sku: str
    name: str
    url: str
    price: float                      # precio actual de venta (COP)
    list_price: Optional[float] = None  # precio "antes" / de lista, si la tienda lo publica


@dataclass
class Glitch:
    item: Item
    reason: str
    baseline: Optional[float]  # precio de referencia usado
    drop_pct: float            # caída en % (0-100)
