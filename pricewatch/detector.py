"""Detector de errores de tarifa (price glitches).

Reglas (se dispara con la primera que aplique):
1. Caída frente a la mediana histórica >= HISTORY_DROP_PCT.
2. Descuento frente al precio de lista publicado >= LIST_DROP_PCT.
Ambas exigen un precio mínimo de referencia para evitar ruido de productos baratos.
Un precio <= 0 o absurdamente bajo (< MIN_PRICE) se ignora: suele ser dato roto.
"""
import os
from typing import Optional

from .models import Glitch, Item

HISTORY_DROP_PCT = float(os.getenv("HISTORY_DROP_PCT", 40))
LIST_DROP_PCT = float(os.getenv("LIST_DROP_PCT", 60))
MIN_REF_PRICE = float(os.getenv("MIN_REF_PRICE", 50_000))  # COP
MIN_PRICE = float(os.getenv("MIN_PRICE", 1_000))           # COP


def detect(item: Item, baseline: Optional[float]) -> Optional[Glitch]:
    if item.price < MIN_PRICE:
        return None

    if baseline and baseline >= MIN_REF_PRICE:
        drop = (1 - item.price / baseline) * 100
        if drop >= HISTORY_DROP_PCT:
            return Glitch(item, "Caída vs. historial", baseline, round(drop, 1))

    if item.list_price and item.list_price >= MIN_REF_PRICE and item.list_price > item.price:
        drop = (1 - item.price / item.list_price) * 100
        if drop >= LIST_DROP_PCT:
            return Glitch(item, "Descuento vs. precio de lista", item.list_price, round(drop, 1))

    return None
