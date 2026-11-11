import os
from typing import List

import requests

from .models import Glitch

API = "https://api.telegram.org/bot{token}/{method}"


def _token() -> str:
    t = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not t:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN")
    return t


def _call(method: str, **params):
    r = requests.post(API.format(token=_token(), method=method), json=params, timeout=15)
    r.raise_for_status()
    return r.json()


def send(chat_id: str, text: str) -> None:
    _call("sendMessage", chat_id=chat_id, text=text,
          parse_mode="HTML", disable_web_page_preview=False)


def fmt_cop(v: float) -> str:
    return "$" + f"{v:,.0f}".replace(",", ".")


def format_glitch(g: Glitch) -> str:
    i = g.item
    return (
        f"🚨 <b>Posible error de precio</b> en <b>{i.store}</b>\n"
        f"{i.name}\n"
        f"Ahora: <b>{fmt_cop(i.price)}</b>\n"
        f"Antes: {fmt_cop(g.baseline)} (−{g.drop_pct}%)\n"
        f"Motivo: {g.reason}\n"
        f"{i.url}"
    )


def broadcast(chat_ids: List[str], glitch: Glitch) -> None:
    text = format_glitch(glitch)
    for cid in chat_ids:
        try:
            send(cid, text)
        except requests.RequestException as e:
            print(f"[telegram] fallo enviando a {cid}: {e}")


def poll_commands(db) -> None:
    """Procesa /start y /stop para gestionar suscriptores (long polling corto)."""
    offset = int(db.get_kv("tg_offset", "0"))
    data = _call("getUpdates", offset=offset, timeout=0)
    for u in data.get("result", []):
        offset = u["update_id"] + 1
        msg = u.get("message") or {}
        text = (msg.get("text") or "").strip().lower()
        chat = msg.get("chat", {}).get("id")
        if not chat:
            continue
        if text.startswith("/start"):
            db.add_subscriber(chat)
            send(str(chat), "✅ Listo. Te avisaré cuando detecte un posible error de precio. /stop para salir.")
        elif text.startswith("/stop"):
            db.remove_subscriber(chat)
            send(str(chat), "Te desuscribí. Escribe /start para volver.")
    db.set_kv("tg_offset", str(offset))
    db.commit()
